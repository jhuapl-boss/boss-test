#!/usr/bin/env python3
# Copyright 2016 The Johns Hopkins University Applied Physics Laboratory
#
# Licensed under the Apache License, Version 2.0 (the "License');
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
import requests, time, inspect
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from intern.remote.boss import BossRemote
from intern.resource.boss.resource import *

# DEFAULT_DOMAIN = 'integration.theboss.io'
DEFAULT_VERSION = 0.7

# Define cache dimensions #
CACHE_SIZE_X = 512
CACHE_SIZE_Y = 512
CACHE_SIZE_Z = 16


def get_remote(config=None) -> BossRemote:
    """ Create a new Boss remote service
    Returns:
        intern.remote.boss.BossRemote : New remote
    """
    remote = BossRemote(config)
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    remote.project_service.session_send_opts = {'verify': False}
    remote.metadata_service.session_send_opts = {'verify': False}
    remote.volume_service.session_send_opts = {'verify': False}
    return remote


def get_host(remote: BossRemote, section: str='Default') -> str:
    """Extract the default host name from a BossRemote configuration"""
    return remote._config._sections[section]['host']


def get_collection_resource(remote: BossRemote, params: dict) -> CollectionResource:
    """Use the arguments in the class config to create a collection resource object"""
    if 'name' not in params:
        params['name'] = 'collection{0}'.format(hex(round(time.time()))[2:])
    param_names = [str(p.name) for p in inspect.signature(CollectionResource).parameters.values()]
    filtered_params = {k: v for k, v in list(params.items()) if k in param_names}  # Filter unexpected arguments
    collection_resource = CollectionResource(**filtered_params)
    if collection_resource.name in remote.list_collections():
        collection = remote.update_project(collection_resource.name, collection_resource)
        print('Updated collection {0}'.format(collection_resource.name))
    else:
        collection = remote.create_project(collection_resource)
        print('Created collection {0}'.format(collection_resource.name))
    return collection


def get_coordinate_frame_resource(remote: BossRemote, params: dict) -> CoordinateFrameResource:
    """Use the arguments in the class config to create a frame resource object"""
    if 'name' not in params:
        params['name'] = 'frame{0}'.format(hex(round(time.time()))[2:])
    param_names = [str(p.name) for p in inspect.signature(CoordinateFrameResource).parameters.values()]
    filtered_params = {k: v for k, v in list(params.items()) if k in param_names}  # Filter unexpected arguments
    frame_resource = CoordinateFrameResource(**filtered_params)
    if frame_resource.name in remote.list_coordinate_frames():
        coordinate_frame = remote.update_project(frame_resource.name, frame_resource)
        print('Updated frame {0}'.format(frame_resource.name))
    else:
        coordinate_frame = remote.create_project(frame_resource)
        print('Created frame {0}'.format(frame_resource.name))
    return coordinate_frame


def get_experiment_resource(remote: BossRemote, params: dict) -> ExperimentResource:
    """Use the arguments in the class config to create an experiment resource object"""
    if 'name' not in params:
        params['name'] = 'experiment{0}'.format(hex(round(time.time()))[2:])
    param_names = [str(p.name) for p in inspect.signature(ExperimentResource).parameters.values()]
    filtered_params = {k: v for k, v in list(params.items()) if k in param_names}  # Filter unexpected arguments
    exp_resource = ExperimentResource(**filtered_params)
    if exp_resource.name in remote.list_experiments(exp_resource.coll_name):
        experiment = remote.update_project(exp_resource.name, exp_resource)
        print('Updated experiment {0}'.format(exp_resource.name))
    else:
        experiment = remote.create_project(exp_resource)
        print('Created experiment {0}'.format(exp_resource.name))
    return experiment


def get_channel_resource(remote: BossRemote, params: dict) -> ChannelResource:
    """Use the arguments in the class config to create a channel resource object"""
    if 'name' not in params:
        params['name'] = 'channel{0}'.format(hex(round(time.time()))[2:])
    param_names = [str(p.name) for p in inspect.signature(ChannelResource).parameters.values()]
    filtered_params = {k: v for k, v in list(params.items()) if k in param_names}  # Filter unexpected arguments
    chan_resource = ChannelResource(**filtered_params)
    if chan_resource.name in remote.list_channels(chan_resource.coll_name, chan_resource.exp_name):
        channel = remote.update_project(chan_resource.name, chan_resource)
        print('Updated channel {0}'.format(chan_resource.name))
    else:
        channel = remote.create_project(chan_resource)
        print('Created channel {0}'.format(chan_resource.name))
    return channel


def post_obj(remote: BossRemote, url: str, format_accept: str='*/*') -> requests.Response:
    """POST request"""
    token = remote.token_project
    headers = {'content-type': 'application/json',
               'Accept': format_accept,
               'Authorization': 'Token {0}'.format(token)}
    return requests.post(url=url, headers=headers)


def get_obj(remote: BossRemote, url: str, format_accept: str='*/*') -> requests.Response:
    """GET request"""
    token = remote.token_project
    headers = {'content-type': 'application/json',
               'Accept': format_accept,
               'Authorization': 'Token {0}'.format(token)}
    return requests.get(url, params=None, headers=headers)

# def fill_cutout_region(remote: BossRemote, channel, xrange: list, yrange: list, zrange: list,
#                        trange: list = None, resolution: int = 0):
#     """
#     """
#     dx, dy, dz, dt = int(CACHE_SIZE_X/2), int(CACHE_SIZE_Y/2), int(CACHE_SIZE_Z/2), 10
#     print('x range = {0}'.format(xrange))
#     print('y range = {0}'.format(yrange))
#     print('z range = {0}'.format(zrange))
#     print('t range = {0}'.format(trange))
#     for x in range(xrange[0], xrange[-1], dx):
#         for y in range(yrange[0], yrange[-1], dy):
#             for z in range(zrange[0], zrange[-1], dz):
#                 x2 = min(x + dx, xrange[-1])
#                 y2 = min(y + dy, yrange[-1])
#                 z2 = min(z + dz, zrange[-1])
#                 if not trange:
#                     print('Filling region x={0}, y={1}, z={2}...'.format(
#                                          '{0}:{1}'.format(x, x2),
#                                          '{0}:{1}'.format(y, y2),
#                                          '{0}:{1}'.format(z, z2)))
#                     data = numpy_utils.cuboid(x2 - x, y2 - y, z2 - z, None, datatype=channel.datatype)
#                     remote.create_cutout(channel, resolution, [x, x2], [y, y2], [z, z2], data)
#                 else:
#                     for t in range(trange[0], trange[-1], dt):
#                         t2 = min(t + dt, trange[-1])
#                         print('Filling region x={0}, y={1}, z={2}, t={3}...'.format(
#                             '{0}:{1}'.format(x, x2),
#                             '{0}:{1}'.format(y, y2),
#                             '{0}:{1}'.format(z, z2),
#                             '{0}:{1}'.format(t, t2)))
#                         data = numpy_utils.cuboid(channel.datatype, x2 - x, y2 - y, z2 - z, t2 - t)
#                         remote.create_cutout(channel, resolution, [x, x2], [y, y2], [z, z2], data, [t, t2])
#                 time.sleep(0.1)  # Try to avoid overloading the endpoint!
#     print('Done populating region')

# def get_channel(remote: BossRemote, channel_args: dict, class_config: dict, fill_if_new_channel=False) -> Resource:
#     """
#     """
#     if 'name' not in channel_args:
#         channel_args['name'] = 'chan{0}t'.format(round(time.time(), 1) * 10)[:-2]
#     channel_setup = ChannelResource(
#         name=channel_args['name'],
#         collection_name=class_config['collection']['name'],
#         experiment_name=class_config['experiment']['name'],
#         datatype=channel_args['datatype'])
#     if channel_setup.name in remote.list_channels(channel_setup.coll_name, channel_setup.exp_name):
#         channel = remote.update_project(channel_setup.name, channel_setup)
#         print('Updated channel {0}'.format(channel_setup.name))
#     else:
#         channel = remote.create_project(channel_setup)
#         print('Created channel {0}'.format(channel_setup.name))
#         time.sleep(5)
#         if channel and fill_if_new_channel:
#             print('Filling channel {0}'.format(channel_setup.name))
#             xrange = [int(class_config['coordinate_frame']['x_start']),
#                       int(class_config['coordinate_frame']['x_stop'])]
#             yrange = [int(class_config['coordinate_frame']['y_start']),
#                       int(class_config['coordinate_frame']['y_stop'])]
#             zrange = [int(class_config['coordinate_frame']['z_start']),
#                       int(class_config['coordinate_frame']['z_stop'])]
#             trange = [0, int(class_config['experiment']['num_time_samples'])]
#             fill_cutout_region(remote, channel, xrange, yrange, zrange, trange, 0)
#     assert channel is not None
#     return channel