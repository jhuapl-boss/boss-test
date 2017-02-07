from urllib2 import Request, urlopen, HTTPError
from urllib import urlencode

def request(url, headers = {}):
    req = Request(url,
                  headers = headers)

    print(url)

    try:
        res = urlopen(req).read()
        print(res)
    except HTTPError as e:
        print(e)

def handler(event, context):
    token = event['token']
    urls = event['urls']

    headers = {
        'Authorization': 'Token {}'.format(token),
    }

    for url in urls:
        request(url,
                headers = headers)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: {} token url [, url ...]".format(sys.argv[0]))

    args = {
        'token': sys.argv[1],
        'urls': sys.argv[2:],
    }

    handler(args, None)
