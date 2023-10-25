#! /usr/bin/env python
'''Share a file'''

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
    return assert_valid_schema(req_body, constants.SHARE_FILE_JSON_SCHEMA)


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


def send_file_link(file_owner, email, file_presigned_url):
    '''Send an email with the download link'''
    body = '''
                 Hi dear Cador,<br>
                 A new file has been shared with you by {}<br />

                 If you want to download it, please click the link below (valid for one hour):<br />

                 {}<br />

                 Sincerely,

                 TheCadors team

         '''.format(
             file_owner,
             file_presigned_url
         )
    message = {
        'Subject': {
            'Data': 'A new Cador file'
        },
        'Body': {
            'Html': {
                'Data': body
            }
        }
    }
    ses_client = boto3.client('ses')
    try:
        response = ses_client.send_email(
            Source = os.environ['SENDER_EMAIL'],
            Destination = {
                'ToAddresses': [email]
            },
            Message = message,
            SourceArn=os.environ['SENDER_SES_ARN'],
        )
        print(response)
    except Exception as error:
        print('Cannot send the email!')
        print(error)
        return 500, {'message': 'Internal server error'}


def share_file(user_id, file_owner, file_infos, req_body, conf_values):
    '''Share the given file'''
    try:
        file_path = user_id+'/'+file_infos['file_name']['S']
        bucket_name = os.environ['USER_FILES_BUCKET']
        s3_client = boto3.client('s3', conf_values['REGION'])
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_path
            },
            ExpiresIn=3600
        )
        file_presigned_url = response
        for email in req_body['share_with']:
            send_file_link(file_owner, email, file_presigned_url)
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


def build_api_response(file_infos):
    '''Build the API response'''
    response_body = collections.OrderedDict()
    response_body['file_id'] = file_infos['file_id']['S']
    response_body['file_name'] = file_infos['file_name']['S']
    response_body['status'] = 'SHARED'

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
                    'Allow' : 'POST, OPTIONS',
                    'Access-Control-Allow-Methods' : 'POST, OPTIONS',
                    'Access-Control-Allow-Headers' : '*'
                }
            }
        share_file(user_id, name, file_infos, req_body, conf_values)
        response_body = build_api_response(
            file_infos
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
