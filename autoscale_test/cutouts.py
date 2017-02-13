from random import randrange

from intern.remote.boss import BossRemote
from intern.resource.boss.resource import *

def rand_range(start, stop, min_size=None, max_size=None):
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
    x = rand_range(*x) if type(x) == tuple else x
    y = rand_range(*y) if type(y) == tuple else y
    z = rand_range(*z) if type(z) == tuple else z

    fmt = 'https://{}/v0.7/cutout/{}/{}/{}/{}/{}/{}/{}/'
    url = fmt.format(host, col, exp, chan, res, x, y, z)
    if t:
        t = rand_range(*t) if type(t) == tuple else t
        url += '{}/'.format(t)
    return url

def gen_urls(args):
    config = {'protocol': 'https',
              'host': args.hostname,
              'token': args.token}

    boss = BossRemote(config)
    results = []

    try:
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
    except Exception as e:
        print("Error generating URLs: {}".format(e))

    return results

def gen_results(total, seq):
    results = []
    d, m = divmod(total, len(seq))
    for i in range(d):
        for s in seq:
            results.append(gen_url(*s))
    for s in seq[:m]:
        results.append(gen_url(*s))
    return results

