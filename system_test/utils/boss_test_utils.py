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


import requests, numpy, re, time, ndio
from ndio.ndresource.boss.resource import *
from ndio.remote.boss.remote import Remote

# Possibly move these variables somewhere else #
DEFAULT_DOMAIN = "api.theboss.io"
DEFAULT_VERSION = BOSS_DEFAULT_VERSION

# Define cache dimensions #
CACHE_SIZE_X = 512
CACHE_SIZE_Y = 512
CACHE_SIZE_Z = 16


def new_remote() -> Remote:
    """ Create a new ndio remote service
    Returns:
        ndio.service.service.Service : New remote
    """
    rmt = Remote()
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    rmt.project_service.session_send_opts = {'verify': False}
    rmt.metadata_service.session_send_opts = {'verify': False}
    rmt.volume_service.session_send_opts = {'verify': False}
    assert rmt is not None
    return rmt

def cuboid(datatype: str, xsize: int, ysize: int, zsize: int, tsize: int = 0, max_bytes=50000000):
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
    data = numpy.random.randint(1, high=high, dtype=datatype,
                             size=(zsize, ysize, xsize) if tsize <= 1 else (tsize, zsize, ysize, xsize))
    if bool(max_bytes):
        assert sys.getsizeof(data) <= max_bytes, "Cuboid size {0} exceeds {1} bytes".format(data.shape, max_bytes)
    return data


def fill_cutout_region(remote: Remote, channel, xrange: list, yrange: list, zrange: list,
                       trange: list = None, resolution: int = 0):
    """
    """
    dx, dy, dz, dt = CACHE_SIZE_X, CACHE_SIZE_Y, 5*CACHE_SIZE_Z, 14
    for x in range(xrange[0], xrange[-1], dx):
        for y in range(yrange[0], yrange[-1], dy):
            for z in range(zrange[0], zrange[-1], dz):
                x2 = min(x + dx, xrange[-1])
                y2 = min(y + dy, yrange[-1])
                z2 = min(z + dz, zrange[-1])
                if not trange:
                    print('Initializing region x={0}, y={1}, z={2}...'.format(
                                         '{0}:{1}'.format(x, x2),
                                         '{0}:{1}'.format(y, y2),
                                         '{0}:{1}'.format(z, z2) ))
                    data = cuboid(channel.datatype, x2 - x, y2 - y, z2 - z, 0, max_bytes=0)
                    remote.cutout_create(channel, resolution, data=data,
                                         x_range='{0}:{1}'.format(x, x2),
                                         y_range='{0}:{1}'.format(y, y2),
                                         z_range='{0}:{1}'.format(z, z2))
                else:
                    DT = 15
                    for t in range(trange[0], trange[-1], DT):
                        t2 = min(t + DT, trange[-1])
                        print('Initializing region x={0}, y={1}, z={2}, t={3}...'.format(
                            '{0}:{1}'.format(x, x2),
                            '{0}:{1}'.format(y, y2),
                            '{0}:{1}'.format(z, z2),
                            '{0}:{1}'.format(t, t2)))
                        data = cuboid(channel.datatype, x2 - x, y2 - y, z2 - z, t2 - t, max_bytes=0)
                        remote.cutout_create(channel, resolution, data=data,
                                             x_range='{0}:{1}'.format(x, x2),
                                             y_range='{0}:{1}'.format(y, y2),
                                             z_range='{0}:{1}'.format(z, z2),
                                             time_range='{0}:{1}'.format(t, t2))

#
# def get_cutout_url(collection_name:str, experiment_name:str, channel_name:str, resolution,
#                    xrange:str, yrange:str, zrange:str, timerange:str=None):
#     url = "{0}/v{1}/cutout/{2}/{3}/{4}/{5}/{6}/{7}/{8}".format(
#         DOMAIN,
#         VERSION,
#         collection_name,
#         experiment_name,
#         channel_name,
#         resolution,
#         xrange,
#         yrange,
#         zrange,
#         "" if not timerange else timerange)
#     return url
#
#
# def get_image_url(collection_name:str, experiment_name:str, channel_name:str, resolution, orientation:str,
#                    xrange:str, yrange:str, zrange:str, timerange:str=None):
#     return
#
#
# def get_tile_url(collection_name:str, experiment_name:str, channel_name:str, resolution, orientation:str,
#                    tilesize:int, xindex:int, yindex:int, zindex:int, tindex:int=None):
#     return


def parse_param_list(test_params: dict, key: str, is_constant_range=True):
    """ Interpret the range of coordinates along an axis, returning a numeric list. Each argument may be formatted as
    a string ("start:stop" or "start:stop:increment") or a list ([start, stop], [start, stop, increment]).
    Args:
        test_params (dict) : Arguments for a test, specified in the JSON configuration
        key (str) : Name of the key
        is_constant_range (bool) : (Optional) If true, return a 2-element list. If false, and the parameter defines 3
            numbers, then form a range of numbers from the 1st to 2nd numbers, incrementing by the 3rd numbers.
    """
    if isinstance(test_params[key], str) and re.match("^[0-9]+(:[0-9]+)?(:[0-9]+)?$", test_params[key]):
        vals = [int(x) for x in re.split(":", test_params[key])]
    elif isinstance(test_params[key], list) or isinstance(test_params[key], int):
        vals = test_params[key]
    else:
        raise AssertionError("Invalid parameter format")
    if bool(isinstance(vals, list) or isinstance(vals, tuple)):
        if len(vals) > 2 and not is_constant_range:
            vals = list(range(vals[0], vals[1] + int(numpy.sign(vals[2])), vals[2]))
        # elif len(vals) > 2:
        #     vals = [vals[0], vals[1]]
    else:
        vals = list([vals])
    return vals


def get_channel(remote:Remote, channel_args:dict, test_config:dict, fill_if_new_channel=False) -> Resource:
    """
    """
    if 'name' not in channel_args:
        channel_args['name'] = 'newChannel{0}'.format(round(time.time(), 1) * 10)[:-2]
    channel_setup = ChannelResource(
        name=channel_args['name'],
        datatype=channel_args['datatype'],
        collection_name=test_config['collection']['name'],
        experiment_name=test_config['experiment']['name'])
    try:
        channel = remote.project_get(channel_setup)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code==404:
            channel = remote.project_create(channel_setup)
            time.sleep(5)
            if channel and fill_if_new_channel:
                xrange = [int(test_config['coordinate_frame']['x_start']),
                          int(test_config['coordinate_frame']['x_stop'])]
                yrange = [int(test_config['coordinate_frame']['y_start']),
                          int(test_config['coordinate_frame']['y_stop'])]
                zrange = [int(test_config['coordinate_frame']['z_start']),
                          int(test_config['coordinate_frame']['z_stop'])]
                trange = [0, int(test_config['experiment']['max_time_sample'])]
                fill_cutout_region(remote, channel, xrange, yrange, zrange, trange, 0)
        else:
            raise e
    assert channel is not None
    return channel

def setup_boss_resources(test_config:dict):
    rmt = new_remote()
    collection_resource = CollectionResource(name=test_config['collection']['name'])
    try:
        collection = rmt.project_get(collection_resource)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            collection = rmt.project_create(collection_resource)
        else:
            raise e
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
    try:
        coordinate_frame = rmt.project_get(frame_resource)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            coordinate_frame = rmt.project_create(frame_resource)
        else:
            raise e
    assert coordinate_frame is not None
    # Get the experiment #
    experiment_resource = ExperimentResource(
        name=test_config['experiment']['name'],
        collection_name=test_config['collection']['name'],
        max_time_sample=int(test_config['experiment']['max_time_sample']),
        coord_frame=coordinate_frame.id)
    try:
        experiment = rmt.project_get(experiment_resource)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            experiment = rmt.project_create(experiment_resource)
        else:
            raise e
    assert experiment is not None
    # Initialize a channel #
    channel = get_channel(rmt, test_config['channel'], test_config, True)
    assert channel is not None


def post_obj(remote, url, format_accept="*/*"):
    token = remote.token_project
    headers = {'content-type': 'application/json',
               'Accept':format_accept,
               'Authorization': 'Token {0}'.format(token)}
    return requests.post(url=url, headers=headers)


def get_obj(remote, url, format_accept="*/*"):
    token = remote.token_project
    headers = {'content-type': 'application/json',
               'Accept':format_accept,
               'Authorization': 'Token {0}'.format(token)}
    return requests.get(url, params=None, headers=headers)

# def reset_cache(self, remote: Remote, channel: Resource, datatype: str, resolution: int = 0):
#     data = self.cuboid(datatype, 1, 1, 1)
#     xstop, ystop, zstop = [self.json()['resources']['coordinate_frame'][k + '_stop'] for k in ['x', 'y', 'z']]
#     xstr, ystr, zstr = ['{0}:{1}'.format(q - 1, q) for q in [xstop, ystop, zstop]]
#     print('Reset cache: Create cutout of size {0}/shape {4} in range x={1}, y={2}, z={3}'.format(
#         data.size, xstr, ystr, zstr, data.shape))
#     remote.cutout_create(channel, resolution, data=data, x_range=xstr, y_range=ystr, z_range=zstr, time_range=None)
#     time.sleep(2)
#     print('Reset cache: Get cutout of size {0}/shape {4} in range x={1}, y={2}, z={3}'.format(
#         data.size, xstr, ystr, zstr, data.shape))
#     remote.cutout_get(channel, resolution, x_range=xstr, y_range=ystr, z_range=zstr, time_range=None)
#     time.sleep(2)
#     return
