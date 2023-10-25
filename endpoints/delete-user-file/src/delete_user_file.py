#! /usr/bin/env python
'''Delete the given user file'''

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


def is_file_owned_by_user(user_id, file_id):
    '''Check if the file is owned by the given user'''
    client = boto3.client('dynamodb')
    response = client.query(
        TableName=os.environ['FILE_SHARING_TABLE'],
        Select='ALL_ATTRIBUTES',
        KeyConditionExpression = 'file_id=:file_id',
        FilterExpression='user_id=:user_id',
        ExpressionAttributeValues={
            ':file_id': {'S':file_id},
            ':user_id': {'S':user_id }
        }
    )
    if len(response['Items']) > 0:
        return True, response['Items'][0]
    return False, None


def is_user_authorized(user_id, event):
    '''Check if the user is authorized to delete the file'''
    url_user_id = event['path'].split('/')[3]
    file_id = event['path'].split('/')[5]
    if url_user_id != user_id:
        return False, None
    is_owned_by_user, file_infos = is_file_owned_by_user(user_id, file_id)
    if not is_owned_by_user:
        return False, None
    return True, file_infos


def delete_file(user_id, file_infos):
    '''Delete the given file'''
    try:
        s3_client = boto3.client('s3', os.getenv(constants.REGION))
        s3_client.delete_object(
            Bucket=os.environ['USER_FILES_BUCKET'],
            Key=user_id+'/'+file_infos['file_name']['S']
        )
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['FILE_SHARING_TABLE'])
        response = table.delete_item(
          Key={
            'file_id': file_infos['file_id']['S']
          },
        )
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


def build_api_response(user_id, file_infos):
    '''Build the API response'''
    response_body = collections.OrderedDict()
    response_body['user_id'] = user_id
    response_body['file_id'] = file_infos['file_id']['S']
    response_body['file_name'] = file_infos['file_name']['S']
    response_body['file_status'] = 'DELETED'
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
        is_authorized, file_infos = is_user_authorized(user_id, event)
        if not is_authorized: 
            return {
                'statusCode': 401,
                'body': json.dumps(
                    {'message': 'User not authorized to perform this action'}
                ),
                'headers': {
                    'Content-Type' : 'application/json',
                    'Access-Control-Allow-Origin' : '*',
                    'Allow' : 'DELETE, OPTIONS',
                    'Access-Control-Allow-Methods' : 'DELETE, OPTIONS',
                    'Access-Control-Allow-Headers' : '*'
                }
            }
        delete_file(user_id, file_infos)
        response_body = build_api_response(
            user_id,
            file_infos
        )
        return {
            'statusCode': 200,
            'body': json.dumps(response_body),
            'headers': {
                'Content-Type' : 'application/json',
                'Access-Control-Allow-Origin' : '*',
                'Allow' : 'DELETE, OPTIONS',
                'Access-Control-Allow-Methods' : 'DELETE, OPTIONS',
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
                'Allow' : 'DELETE, OPTIONS',
                'Access-Control-Allow-Methods' : 'DELETE, OPTIONS',
                'Access-Control-Allow-Headers' : '*'
            },
            'isBase64Encoded': False,
        }
