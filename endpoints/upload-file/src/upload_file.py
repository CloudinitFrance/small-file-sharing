#! /usr/bin/env python
'''Upload a new file'''

import os
import sys
import uuid
import json
import collections
import base64
from os.path import join, dirname
from jsonschema import validate
import jsonschema
import jwt
import boto3
import botocore
from boto3.dynamodb.conditions import Key, Attr
import constants
import log


LOGGER = log.setup_logging()


def _load_json_schema(filename):
    ''' Loads the given schema file '''

    relative_path = join(constants.SCHEMAS_FOLDER, filename)
    absolute_path = join(dirname(__file__), relative_path)

    with open(absolute_path) as schema_file:
        return json.loads(schema_file.read())


def assert_valid_schema(data, schema_file):
    ''' Checks whether the given data matches the schema '''

    schema = _load_json_schema(schema_file)
    try:
        validate(data, schema)
        return True, None
    except jsonschema.exceptions.ValidationError as error:
        return False, error.message


def check_inputs(req_body):
    '''Validate inputs'''
    return assert_valid_schema(req_body, constants.NEW_FILE_JSON_SCHEMA)


def upload_file(user_id, req_body, conf_values):
    '''Upload a new file'''
    try:
        bucket_name = os.environ['USER_FILES_BUCKET']
        decoded_file = base64.b64decode(req_body['file_data'])
        with open('/tmp/temp_file', 'wb') as f:
            f.write(decoded_file)
        s3_client = boto3.client('s3', conf_values['REGION'])
        s3_client.upload_file(
            '/tmp/temp_file',
            bucket_name,
            user_id+'/'+req_body['remote_file_name']
        )
        file_id = str(uuid.uuid4())
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['FILE_SHARING_TABLE'])
        response = table.scan(FilterExpression=Attr('file_name').eq(req_body['remote_file_name']))
        if len(response['Items']) > 0:
            print('File already uploaded, will remove the file_id and updated it with a new one!')
            response = table.delete_item(
              Key={
                'file_id': response['Items'][0]['file_id']
              },
            )
        response = table.put_item(
            Item={
                'file_id': file_id,
                'file_name': req_body['remote_file_name'],
                'user_id': user_id
            }
        )
        return file_id
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


def build_api_response(file_id):
    '''Build the API response'''
    response_body = collections.OrderedDict()
    response_body['file_id'] = file_id
    response_body['status'] = 'UPLOADED'

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
        req_body = json.loads(event['body'])
        is_payload_data_valid, error_msg = check_inputs(req_body)
        if not is_payload_data_valid:
            return {
                'statusCode': 400,
                'body': json.dumps({'message':error_msg}),
                'headers': {
                    'Content-Type' : 'application/json',
                    'Access-Control-Allow-Origin' : '*',
                    'Allow' : 'POST, OPTIONS',
                    'Access-Control-Allow-Methods' : 'POST, OPTIONS',
                    'Access-Control-Allow-Headers' : '*'
                }
            }
        conf_values = init_env_vars()
        claims = get_claims(event['headers']['Authorization'])
        user_id, name, email = get_userinfo(
            claims,
            conf_values
        )
        file_id = upload_file(user_id, req_body, conf_values)
        response_body = build_api_response(
            file_id
        )
        return {
            'statusCode': 201,
            'body': json.dumps(response_body),
            'headers': {
                'Content-Type' : 'application/json',
                'Access-Control-Allow-Origin' : '*',
                'Allow' : 'POST, OPTIONS',
                'Access-Control-Allow-Methods' : 'POST, OPTIONS',
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
                'Allow' : 'POST, OPTIONS',
                'Access-Control-Allow-Methods' : 'POST, OPTIONS',
                'Access-Control-Allow-Headers' : '*'
            },
            'isBase64Encoded': False,
        }
