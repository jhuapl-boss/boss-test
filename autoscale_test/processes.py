import json
import signal
import time

from boto3.session import Session
from botocore.client import Config

def launch_lambda(queue, session_args, token, urls):
    session = Session(**session_args)
    config = Config(read_timeout = 60 * 5)
    client = session.client('lambda', config = config)

    lambda_args = {'token':token, 'queue':queue, 'urls':urls}
    resp = client.invoke(FunctionName = 'AutoScaleTest',
                         #InvocationType = 'Event',
                         #LogType = 'None',
                         Payload = json.dumps(lambda_args).encode('utf-8'))
    #print(resp)
    #print(resp['Payload'].read())
    return resp['Payload'].read()

def aggregate(queue, session_args, timeout=60, retry=3):
    signal.signal(signal.SIGINT, signal.SIG_IGN) # Ignore the KeyboardInterrupt
    total_bytes = 0
    total_seconds = 0
    received_count = 0
    errors = []

    session = Session(**session_args)
    sqs = session.resource('sqs')
    queue = sqs.Queue(queue)

    start = time.time()
    current = time.time()
    #print("Aggregating results")
    while retry > 0:# or int(current - start) < timeout:
        msgs = queue.receive_messages(WaitTimeSeconds=20, MaxNumberOfMessages=10)
        if len(msgs) == 0:
            #print("\tretry")
            retry -= 1
            continue
        print('.', end='', flush=True)
        for msg in msgs:
            queue.delete_messages(Entries = [{'Id':'X', 'ReceiptHandle': msg.receipt_handle}])
            received_count += 1
            msg = json.loads(msg.body)
            if 'error' in msg:
                errors.append(msg['error'])
            else:
                total_bytes += msg['bytes']
                total_seconds += (msg['read_stop'] - msg['req_start'])
        current = time.time()
    return (received_count, (total_bytes, total_seconds), errors)

