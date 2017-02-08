import os
import sys
import argparse
import json
import io
import zipfile
import time
import asyncio

from contextlib import contextmanager
from random import randrange, sample
from boto3.session import Session

from intern.remote.boss import BossRemote
from intern.resource.boss.resource import *

def gen_range(start, stop, min_size=None, max_size=None):
    while True:
        start_ = randrange(start, stop)
        stop_ = randrange(start_+1, stop+1)
        size = stop_ - start_
        if min_size and min_size > size:
            continue
        if max_size and max_size < size:
            continue
        return '{}:{}'.format(start_, stop_)

def gen_url(host, col, exp, chan, res, x, y, z, t=None):
    x = gen_range(*x) if type(x) == tuple else x
    y = gen_range(*y) if type(y) == tuple else y
    z = gen_range(*z) if type(z) == tuple else z

    fmt = 'https://{}/v0.7/cutout/{}/{}/{}/{}/{}/{}/{}/'
    url = fmt.format(host, col, exp, chan, res, x, y, z)
    if t:
        t = gen_range(*t) if type(t) == tuple else t
        url += '{}/'.format(t)
    return url

def gen_urls(args):
    config = {'protocol': 'https',
              'host': args.hostname,
              'token': args.token}

    boss = BossRemote(config)
    results = []

    if args.collection is not None:
        collections = [args.collection]
    else:
        collections = boss.list_collections()

    for collection in collections:
        if args.experiment is not None:
            experiments = [args.experiment]
        else:
            experiments = boss.list_experiments(collection)

        for experiment in experiments:
            if args.channel is not None:
                channels = [args.channel]
            else:
                channels = boss.list_channels(collection, experiment)

            exp = ExperimentResource(name = experiment,
                                     collection_name = collection)
            exp = boss.get_project(exp)

            coord = CoordinateFrameResource(name = exp.coord_frame)
            coord = boss.get_project(coord)

            for channel in channels:
                ch = ChannelResource(name = channel,
                                     experiment_name = experiment,
                                     collection_name = collection)
                ch = boss.get_project(ch)

                def check_range(name, var, start, stop):
                    start_, stop_ = map(int, var.split(':'))
                    if start_ < start:
                        fmt = "{} range start for {}/{}/{} is less than the coordinate frame, setting to minimum"
                        print(fmt.format(name, collection, experiment, channel))
                        start_ = start
                    if stop_ > stop:
                        fmt = "{} range stop for {}/{}/{} is greater than the coordinate frame, setting to maximum"
                        print(fmt.format(name, collection, experiment, channel))
                        stop_ = stop
                    return '{}:{}'.format(start_, stop_)

                if args.x_range:
                    x = check_range('X', args.x_range, coord.x_start, coord.x_stop)
                else:
                    x = (coord.x_start, coord.x_stop, args.min, args.max)

                if args.y_range:
                    y = check_range('Y', args.y_range, coord.y_start, coord.y_stop)
                else:
                    y = (coord.y_start, coord.y_stop, args.min, args.max)

                if args.z_range:
                    z = check_range('Z', args.z_range, coord.z_start, coord.z_stop)
                else:
                    z = (coord.z_start, coord.z_stop, args.min, args.max)

                # Arguments to gen_url
                results.append((args.hostname,
                                collection,
                                experiment,
                                channel,
                                0, x, y, z, None))
    return results

def gen_results(total, seq):
    d, m = divmod(total, len(seq))
    for i in range(d):
        for s in seq:
            yield gen_url(*s)
    for s in seq[:m]:
        yield gen_url(*s)

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
def create_lambda(session, role):
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
                                  Timeout = 60,
                                  MemorySize = 128) # MBs, multiple of 64

    try:
        yield resp['FunctionArn']
    finally:
        resp = client.delete_function(FunctionName = 'AutoScaleTest')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "BOSS API Autoscale Test Script",
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aws-credentials", "-a",
                        metavar = "<file>",
                        default = os.environ.get("AWS_CREDENTIALS"),
                        type = argparse.FileType('r'),
                        help = "File with credentials to use when connecting to AWS (default: AWS_CREDENTIALS)")
    parser.add_argument("--collection", "-c", help = "Target collection")
    parser.add_argument("--experiment", "-e", help = "Target experiment")
    parser.add_argument("--channel", "-n", help = "Target channel")
    parser.add_argument("--x_range", "-x", help = "Target x range")
    parser.add_argument("--y_range", "-y", help = "Target y range")
    parser.add_argument("--z_range", "-z", help = "Target z range")
    parser.add_argument("--min", type=int, help = "Minimum cutout size")
    parser.add_argument("--max", type=int, help = "Maximum cutout size")
    parser.add_argument("--unique", "-u", type=int, help = "Number of channels to target")
    parser.add_argument("--total", "-t", default=100, type=int, help = "Total number of requests to make")
    parser.add_argument("--lambdas", "-l", default=5, type=int, help = "Total number of lambdas to create")
    parser.add_argument("token", help="BOSS API Token")
    parser.add_argument("hostname", help="Pulic hostname of the target BOSS API server")

    args = parser.parse_args()

    if args.aws_credentials is None:
        parser.print_usage()
        print("Error: AWS credentials not provided and AWS_CREDENTIALS is not defined")
        sys.exit(1)

    creds = json.load(args.aws_credentials)
    session = Session(aws_access_key_id = creds['aws_access_key'],
                      aws_secret_access_key = creds['aws_secret_key'],
                      region_name = creds.get('aws_region', 'us-east-1'))

    # Generate the unique target channels
    print("Generating URLs")
    urls = gen_urls(args)
    if args.unique:
        if args.unique >= len(urls):
            print("Only {} unique urls, not using --unique argument".format(len(urls)))
        else:
            urls = sample(urls, args.unique)
    if len(urls) > args.total:
        urls = sample(urls, args.total)

    # Generate unique urls
    results = list(gen_results(args.total, urls))

    # Split urls into groups for each lambda
    results = [results[i::args.lambdas] for i in range(args.lambdas)]
    print("\tComplete")

    print("Creating AWS Resources")
    client = session.client('lambda')
    with create_queue(session) as queue:
        with create_role(session) as role:
            with create_lambda(session, role) as target:
                print("\tComplete")
                for i in range(args.lambdas):
                    print("{:7.2%} Launching lambdas\r".format(i/args.lambdas), end='', flush=True)
                    lambda_args = {'token':args.token, 'queue':queue.url, 'urls': results[i]}
                    resp = client.invoke(FunctionName = 'AutoScaleTest',
                                         InvocationType = 'Event',
                                         #LogType = 'None',
                                         Payload = json.dumps(lambda_args).encode('utf-8'))
                    #print(resp)
                print("Finished launching lambdas")

                total_bytes = 0
                total_seconds = 0
                total_errors = 0
                try:
                    for i in range(args.total):
                        print("{:7.2%} Waiting for messages\r".format(i/args.total), end='', flush=True)

                        msg = queue.receive_messages(WaitTimeSeconds=20)
                        if len(msg) == 0:
                            print("Could not get message {}          ".format(i))
                            continue
                        msg = msg[0]
                        queue.delete_messages(Entries = [{'Id':'X', 'ReceiptHandle': msg.receipt_handle}])
                        msg = json.loads(msg.body)
                        if 'error' in msg:
                            total_errors += 1
                        else:
                            total_bytes += msg['bytes']
                            total_seconds += (msg['read_stop'] - msg['req_start'])
                    print("Finished waiting for messages")
                    print()

                    input("press any key to delete lambda")
                finally:
                    # Always print, even if there was a CTRL+C
                    print()
                    print("Received {:,} messages".format(args.total))
                    print("Number of errors {:,}".format(total_errors))
                    print("Throughput {:,} b/s".format(int(total_bytes / total_seconds)))
                    print()

