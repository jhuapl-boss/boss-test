#!/usr/bin/env python3
# Copyright 2016 The Johns Hopkins University Applied Physics Laboratory
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DEFAULT_DOMAIN = "api-davismj1.thebossdev.io"
DEFAULT_VERSION = 0.7

import requests, numpy, re, time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from intern.resource import Resource
from intern.remote.boss import BossRemote
from intern.resource.boss import *
from intern.resource.boss.resource import *

# Define cache dimensions #
CACHE_SIZE_X = 512
CACHE_SIZE_Y = 512
CACHE_SIZE_Z = 16


def new_remote(config=None) -> BossRemote:
    """ Create a new Boss remote service
    Returns:
        intern.remote.boss.BossRemote : New remote
    """
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    rmt = BossRemote(config)
    assert rmt is not None
    rmt.project_service.session_send_opts = {'verify': False}
    rmt.metadata_service.session_send_opts = {'verify': False}
    rmt.volume_service.session_send_opts = {'verify': False}
    return rmt


def cuboid(datatype: str, xsize: int, ysize: int, zsize: int, tsize=None, max_bytes=50000000):
    """ Generate a datacube of random numbers. Range of possible values is from 1 up to
    the highest possible value of a numpy datatype.
    Args:
        datatype (str) : Name of the numpy datatype
        xsize (int) : Size of the x-dimension
        ysize (int) : Size of the y-dimension
        zsize (int) : Size of the z-dimension
        tsize (int) : Optional, Size of the time dimension (default is 0)
        max_bytes (int) : Optional, limit on the size of the data in bytes (default is ~50 MB)
    Returns:
        4D or 3D numpy array of random numbers, ranging from 1 up to the maximum value of the datatype
    """
    import sys
    s = re.search('int|float', datatype)
    high = 2 if (not s) else numpy.iinfo(datatype).max if (s.group(0) == 'int') else numpy.finfo(datatype).max
    dims = (zsize, ysize, xsize) if not bool(tsize) else (tsize, zsize, ysize, xsize)
    data = numpy.random.randint(1, high, dims, datatype)
    if bool(max_bytes):
        assert sys.getsizeof(data) <= max_bytes, "Cuboid size {0} exceeds {1} bytes".format(data.shape, max_bytes)
    return data


def fill_cutout_region(remote: BossRemote, channel, xrange: list, yrange: list, zrange: list,
                       trange: list = None, resolution: int = 0):
    """
    """
    dx, dy, dz, dt = int(CACHE_SIZE_X/2), int(CACHE_SIZE_Y/2), int(CACHE_SIZE_Z/2), 10
    print('x range = {0}'.format(xrange))
    print('y range = {0}'.format(yrange))
    print('z range = {0}'.format(zrange))
    print('t range = {0}'.format(trange))
    for x in range(xrange[0], xrange[-1], dx):
        for y in range(yrange[0], yrange[-1], dy):
            for z in range(zrange[0], zrange[-1], dz):
                x2 = min(x + dx, xrange[-1])
                y2 = min(y + dy, yrange[-1])
                z2 = min(z + dz, zrange[-1])
                if not trange:
                    print('Filling region x={0}, y={1}, z={2}...'.format(
                                         '{0}:{1}'.format(x, x2),
                                         '{0}:{1}'.format(y, y2),
                                         '{0}:{1}'.format(z, z2) ))
                    data = cuboid(channel.datatype, x2 - x, y2 - y, z2 - z, None)
                    remote.create_cutout(channel, resolution, [x,x2], [y,y2], [z,z2], data)
                else:
                    for t in range(trange[0], trange[-1], dt):
                        t2 = min(t + dt, trange[-1])
                        print('Filling region x={0}, y={1}, z={2}, t={3}...'.format(
                            '{0}:{1}'.format(x, x2),
                            '{0}:{1}'.format(y, y2),
                            '{0}:{1}'.format(z, z2),
                            '{0}:{1}'.format(t, t2)))
                        data = cuboid(channel.datatype, x2 - x, y2 - y, z2 - z, t2 - t)
                        remote.create_cutout(channel, resolution, [x, x2], [y, y2], [z, z2], data, [t,t2])
                time.sleep(1)
    print('Done populating region')


def parse_param_list(test_params: dict, key: str, is_constant_range=True):
    """ Interpret the range of coordinates along an axis, returning a numeric list. Each argument may be formatted as
    a string ("start:stop" or "start:stop:increment") or a list ([start, stop], [start, stop, increment]).
    Args:
        test_params (dict) : Arguments for a test, specified in the JSON configuration
        key (str) : Name of the key
        is_constant_range (bool) : (Optional) If true, return a 2-element list. If false, and the parameter defines 3
            numbers, then form a range of numbers from the 1st to 2nd numbers, incrementing by the 3rd numbers.
    """
    # if isinstance(test_params[key], str) and re.match("^[0-9]+(:[0-9]+)?(:[0-9]+)?$", test_params[key]):
    #     vals = [int(x) for x in re.split(":", test_params[key])]
    if isinstance(test_params[key], list) or isinstance(test_params[key], int):
        vals = test_params[key]
    else:
        raise AssertionError("Invalid parameter format")
    if bool(isinstance(vals, list) or isinstance(vals, tuple)):
        if len(vals) > 2 and not is_constant_range:
            vals = list(range(vals[0], vals[1] + int(numpy.sign(vals[2])), vals[2]))
    else:
        vals = list([vals])
    return vals


def get_channel(remote:BossRemote, channel_args:dict, test_config:dict, fill_if_new_channel=False) -> Resource:
    """
    """
    if 'name' not in channel_args:
        channel_args['name'] = 'chan{0}t'.format(round(time.time(), 1) * 10)[:-2]
    channel_setup = ChannelResource(
        name=channel_args['name'],
        collection_name=test_config['collection']['name'],
        experiment_name=test_config['experiment']['name'],
        datatype=channel_args['datatype'])
    if channel_setup.name in remote.list_channels(channel_setup.coll_name, channel_setup.exp_name):
        channel = remote.update_project(channel_setup.name, channel_setup)
        print("Updated channel {0}".format(channel_setup.name))
    else:
        channel = remote.create_project(channel_setup)
        print("Created channel {0}".format(channel_setup.name))
        time.sleep(5)
        if channel and fill_if_new_channel:
            print("Filling channel {0}".format(channel_setup.name))
            xrange = [int(test_config['coordinate_frame']['x_start']),
                      int(test_config['coordinate_frame']['x_stop'])]
            yrange = [int(test_config['coordinate_frame']['y_start']),
                      int(test_config['coordinate_frame']['y_stop'])]
            zrange = [int(test_config['coordinate_frame']['z_start']),
                      int(test_config['coordinate_frame']['z_stop'])]
            trange = [0, int(test_config['experiment']['num_time_samples'])]
            fill_cutout_region(remote, channel, xrange, yrange, zrange, trange, 0)
    assert channel is not None
    return channel


def delete_channel(remote:BossRemote, channel:Resource):
    time.sleep(1)
    remote.delete_project(channel)


def setup_boss_resources(test_config:dict):
    """
    """
    rmt = new_remote()
    collection_resource = CollectionResource(name=test_config['collection']['name'])
    if collection_resource.name in rmt.list_collections():
        collection = rmt.update_project(collection_resource.name, collection_resource)
        print("Updated collection {0}".format(collection_resource.name))
    else:
        collection = rmt.create_project(collection_resource)
        print("Created collection {0}".format(collection_resource.name))
    assert collection is not None
    # Get the coordinate frame #
    frame_resource = CoordinateFrameResource(
        name=test_config['coordinate_frame']['name'],
        x_start=int(test_config['coordinate_frame']['x_start']),
        x_stop=int(test_config['coordinate_frame']['x_stop']),
        y_start=int(test_config['coordinate_frame']['y_start']),
        y_stop=int(test_config['coordinate_frame']['y_stop']),
        z_start=int(test_config['coordinate_frame']['z_start']),
        z_stop=int(test_config['coordinate_frame']['z_stop']))
    if frame_resource.name in rmt.list_coordinate_frames():
        coordinate_frame = rmt.update_project(frame_resource.name, frame_resource)
        print("Updated frame {0}".format(frame_resource.name))
    else:
        coordinate_frame = rmt.create_project(frame_resource)
        print("Created frame {0}".format(frame_resource.name))
    assert coordinate_frame is not None
    # Get the experiment #
    experiment_resource = ExperimentResource(
        name=test_config['experiment']['name'],
        collection_name=test_config['collection']['name'],
        num_time_samples=int(test_config['experiment']['num_time_samples']),
        coord_frame=coordinate_frame.name)
    if experiment_resource.name in rmt.list_experiments(collection_resource.name):
        experiment = rmt.update_project(experiment_resource.name, experiment_resource)
        print("Updated experiment {0}".format(experiment_resource.name))
    else:
        experiment = rmt.create_project(experiment_resource)
        print("Created experiment {0}".format(experiment_resource.name))
    assert experiment is not None
    # Initialize a channel #
    channel = get_channel(rmt, test_config['channel'], test_config, True)


def post_obj(remote:BossRemote, url, format_accept="*/*"):
    """
    """
    token = remote.token_project
    headers = {'content-type': 'application/json',
               'Accept':format_accept,
               'Authorization': 'Token {0}'.format(token)}
    return requests.post(url=url, headers=headers)


def get_obj(remote:BossRemote, url, format_accept="*/*"):
    """
    """
    token = remote.token_project
    headers = {'content-type': 'application/json',
               'Accept':format_accept,
               'Authorization': 'Token {0}'.format(token)}
    return requests.get(url, params=None, headers=headers)
