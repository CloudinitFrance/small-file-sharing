#! /usr/bin/env python
'''Get user files'''

import os
import sys
import uuid
import json
import collections
import base64
from os.path import join, dirname
import jwt
import boto3
import botocore
from boto3.dynamodb.conditions import Key, Attr
import constants
import log


LOGGER = log.setup_logging()


def get_user_files(user_id):
    '''Get user files'''
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['FILE_SHARING_TABLE'])
        response = table.scan(FilterExpression=Attr('user_id').eq(user_id))
        user_files = []
        for user_file in response['Items']:
            user_files.append(
                {
                    'file_id': user_file['file_id'],
                    'file_name': user_file['file_name']
                }
            )
        return user_files
    except Exception as error:
        LOGGER.error(error)
        raise Exception('Internal server error')


def get_userinfo(claims, conf_values):
    '''Get user infos'''
    try:
        cup_client = boto3.client('cognito-idp', conf_values['REGION'])
        response = cup_client.admin_get_user(
            UserPoolId=conf_values['COGNITO_USER_POOL_ID'],
            Username=claims['cognito:username']
        )
        if 'Username' in response:
            user_id = response['Username']
        else:
            user_id = None
        email = None
        name = None
        print(response)
        for attr in response['UserAttributes']:
            if attr['Name'] == 'name':
                name = attr['Value']
            elif attr['Name'] == 'email':
                email = attr['Value']
            else:
                pass
        return user_id, name, email
    except Exception as error:
        raise Exception('Error: {}'.format(error))


def get_claims(jwt_token):
    '''Extract claims from the JWT token'''
    try:
        decode = jwt.decode(
            jwt_token.split(' ')[1],
            algorithms=['RS256'],
            options={"verify_signature": False}
        )
    except Exception as error:
        LOGGER.error(error)
    return decode


def build_api_response(user_id, user_files):
    '''Build the API response'''
    response_body = collections.OrderedDict()
    response_body['user_id'] = user_id
    response_body['user_files'] = []
    for user_file in user_files:
        response_body['user_files'].append(user_file)
    return response_body


def init_env_vars():
    '''Get all environment variables'''
    conf_values = {}
    conf_values['REGION'] = os.getenv(constants.REGION)
    conf_values['COGNITO_USER_POOL_ID'] = os.getenv(constants.COGNITO_USER_POOL_ID)
    return conf_values


def lambda_handler(event, _):
    '''Lambda entrypoint'''
    try:
        conf_values = init_env_vars()
        claims = get_claims(event['headers']['Authorization'])
        user_id, name, email = get_userinfo(
            claims,
            conf_values
        )
        user_files = get_user_files(user_id)
        response_body = build_api_response(
            user_id,
            user_files
        )
        return {
            'statusCode': 200,
            'body': json.dumps(response_body),
            'headers': {
                'Content-Type' : 'application/json',
                'Access-Control-Allow-Origin' : '*',
                'Allow' : 'GET, OPTIONS',
                'Access-Control-Allow-Methods' : 'GET, OPTIONS',
                'Access-Control-Allow-Headers' : '*'
            },
            'isBase64Encoded': False,
        }
    except Exception as error:
        err_msg = {'error_message': '{}'.format(error)}
        LOGGER.error(err_msg)
        #TODO: Perform necessary rollback
        return {
            'statusCode': 400,
            'body': json.dumps(err_msg),
            'headers': {
                'Content-Type' : 'application/json',
                'Access-Control-Allow-Origin' : '*',
                'Allow' : 'GET, OPTIONS',
                'Access-Control-Allow-Methods' : 'GET, OPTIONS',
                'Access-Control-Allow-Headers' : '*'
            },
            'isBase64Encoded': False,
        }
