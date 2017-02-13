import os
import sys
import argparse
import json
import time
import signal

from random import sample
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
from boto3.session import Session

from cutouts import gen_urls, gen_results
from resources import create_queue, create_role, create_lambda
from processes import launch_lambda, aggregate

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
    session_args = {
        'aws_access_key_id' : creds['aws_access_key'],
        'aws_secret_access_key' : creds['aws_secret_key'],
        'region_name' : creds.get('aws_region', 'us-east-1'),
    }
    session = Session(**session_args)

    # Generate the unique target channels
    print("Generating URLs")
    urls = gen_urls(args)
    if len(urls) == 0:
        sys.exit(1)
    if args.unique:
        if args.unique >= len(urls):
            print("Only {} unique urls, not using --unique argument".format(len(urls)))
        else:
            urls = sample(urls, args.unique)
    if len(urls) > args.total:
        urls = sample(urls, args.total)

    # Generate unique urls
    results = gen_results(args.total, urls)

    # Split urls into groups for each lambda
    results = [results[i::args.lambdas] for i in range(args.lambdas)]
    print("\tComplete")

    print("Creating AWS Resources")
    client = session.client('lambda')
    with create_queue(session) as queue:
        with create_role(session) as role:
            lambda_timeout = 60 * 5
            with create_lambda(session, role, lambda_timeout) as target:
                print("\tComplete")
                tpool = Pool(processes = args.lambdas)
                pool = Pool(processes = min(args.lambdas, 10))
                
                lambda_args = [(queue.url, session_args, args.token, r) for r in results]
                #pool.starmap(launch_lambda, lambda_args)
                lambdas = pool.starmap_async(launch_lambda, lambda_args)
                print("Finished launching lambdas")

                total_bytes = 0
                total_seconds = 0
                total_time = 0
                received_count = 0
                errors = []
                try:

                    def dup(count, *args):
                        results = []
                        for i in range(count):
                            results.append(args)
                        return results
                    
                    start = time.time()
                    print("Waiting for messages", end='', flush=True)

                    #while received_count < args.total or not lambdas.ready():
                    while not lambdas.ready():
                        results = pool.starmap(aggregate, dup(pool._processes, queue.url, session_args, 60))
                        for count, (bytes_, seconds), errors_ in results:
                            received_count += count
                            total_bytes += bytes_
                            total_seconds += seconds
                            errors.extend(errors_)
                        print("\nReceived {} messages".format(received_count), flush=True)
                        print("Lambdas finished? {}".format(lambdas.ready()), flush=True)

                    print("Finished waiting for messages", flush=True)
                    print()
                    total_time = time.time() - start


                    #input("press any key to delete lambda")
                except KeyboardInterrupt:
                    pass
                finally:
                    print("Lambda results")
                    for res in lambdas.get():
                        if res != b'null':
                            print(res)
                    print()
                    tpool.terminate()
                    pool.terminate()
                    # Always print, even if there was a CTRL+C
                    print()
                    print("Elapsed time: {} seconds".format(total_time))
                    print("Received {:,} messages".format(received_count))
                    print("Number of errors {:,}".format(len(errors)))
                    keys = set(errors)
                    values = list(errors)
                    for key in keys:
                        print("\t{} x '{}'".format(values.count(key), key))
                    if total_seconds == 0:
                        print("Zero seconds of data recorded")
                    else:
                        print("Throughput {:,} b/s".format(int(total_bytes / total_seconds)))
                    print()

                input("Press any key to cleanup")
