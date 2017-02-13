import io
import zipfile
import time
import json

from contextlib import contextmanager

@contextmanager
def create_queue(session):
    sqs = session.resource('sqs')
    client = session.client('sqs')
    resp = client.create_queue(QueueName = 'AutoScaleTest',
                               Attributes = {
                               })

    try:
        url = resp['QueueUrl']
        yield sqs.Queue(url)
    finally:
        resp = client.delete_queue(QueueUrl = resp['QueueUrl'])
        print("Waiting 60 seconds for queue to be deleted")
        time.sleep(60)

@contextmanager
def create_role(session):
    policy = {
        'Version': '2012-10-17',
        'Statement': [{
            'Effect': 'Allow',
            'Principal': {
                'Service': 'lambda.amazonaws.com',
            },
            'Action': 'sts:AssumeRole',
        }]
    }
    client = session.client('iam')
    resp = client.create_role(RoleName = 'AutoScaleTest',
                              AssumeRolePolicyDocument = json.dumps(policy))
    role_arn = resp['Role']['Arn']

    try:
        policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Action': [
                    'sqs:SendMessage',
                ],
                'Resource': [
                    '*'
                ],
            }]
        }

        resp = client.create_policy(PolicyName = 'AutoScaleTest',
                                    PolicyDocument = json.dumps(policy))
        policy_arn = resp['Policy']['Arn']

        try:
            resp = client.attach_role_policy(RoleName = 'AutoScaleTest',
                                             PolicyArn = policy_arn)

            try:
                time.sleep(6) # wait for role to become avalable to lambda)))

                yield role_arn
            finally:
                resp = client.detach_role_policy(RoleName = 'AutoScaleTest',
                                                 PolicyArn = policy_arn)
        finally:
            resp = client.delete_policy(PolicyArn = policy_arn)
    finally:
        resp = client.delete_role(RoleName = 'AutoScaleTest')

@contextmanager
def create_lambda(session, role, timeout):
    with open('lambda.py', 'r') as fh:
        lambda_code = fh.read().replace('"', '\"').replace('\\', '\\\\')

    code = io.BytesIO()
    archive = zipfile.ZipFile(code, mode='w')
    archive_file = zipfile.ZipInfo('index.py')
    archive_file.external_attr = 0o777 << 16
    archive.writestr(archive_file, lambda_code)
    archive.close()
    lambda_code = code.getvalue()

    client = session.client('lambda')
    resp = client.create_function(FunctionName = 'AutoScaleTest',
                                  Runtime = 'python2.7',
                                  Role = role,
                                  Handler = 'index.handler',
                                  Code = {'ZipFile': lambda_code},
                                  Description = 'AutoScale test lambda',
                                  Timeout = timeout,
                                  MemorySize = 128) # MBs, multiple of 64

    try:
        yield resp['FunctionArn']
    finally:
        resp = client.delete_function(FunctionName = 'AutoScaleTest')

