import json
import boto3
from time import time as now

from urllib2 import Request, urlopen, HTTPError
from urllib import urlencode

def request(queue, url, headers = {}):
    msg = {'start': now()}

    try:
        req = Request(url,
                      headers = headers)

        msg['req_start'] = now()
        resp = urlopen(req)
        msg['read_start'] = msg['req_stop'] = now()
        msg['code'] = resp.getcode()
        data = resp.read()
        msg['bytes'] = len(data)
        msg['read_stop'] = now()
    except HTTPError as e:
        msg['error_start'] = now()
        msg['code'] = e.code
        msg['error'] = str(e)
        msg['error_stop'] = now()
    except Exception as e:
        msg['error'] = str(e)

    msg['stop'] = now()

    try:
        queue.send_message(MessageBody = json.dumps(msg))
    except Exception as e:
        print("{}: {}".format(e, msg))


def handler(event, context):
    token = event['token']
    urls = event['urls']

    sqs = boto3.resource('sqs')
    queue = sqs.Queue(event['queue'])

    headers = {
        'Authorization': 'Token {}'.format(token),
    }

    for url in urls:
        request(queue, url,
                headers = headers)

