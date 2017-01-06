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


def set_channel_resource(remote: BossRemote, params: dict) -> ChannelResource:
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


def delete_channel(remote: BossRemote, channel, coll_name=None, exp_name=None):
    chan_obj = None
    if isinstance(channel, ChannelResource):
        chan_obj = channel
    elif isinstance(channel, str) and coll_name is not None and exp_name is not None:
        chan_name = channel
        chan_obj = remote.get_project(ChannelResource(name=chan_name, experiment_name=exp_name))
    if chan_obj is not None:
        print('Deleting channel "{0}"...'.format(chan_obj.name))
        remote.delete_project(chan_obj)


def set_experiment_resource(remote: BossRemote, params: dict) -> ExperimentResource:
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


def delete_experiment(remote: BossRemote, experiment, coll_name=None):
    exp_obj = None
    exp_name = None
    if isinstance(experiment, ExperimentResource):
        exp_obj = experiment
        exp_name = experiment.name
        coll_name = experiment.coll_name
    elif isinstance(experiment, str) and coll_name is not None:
        exp_name = experiment
        exp_obj = remote.get_project(ExperimentResource(name=exp_name, collection_name=coll_name))
    if exp_name is not None:
        print('Deleting channels of experiment "{0}"...'.format(exp_name))
        chan_names = remote.list_channels(coll_name, exp_name)
        for n in chan_names:
            delete_channel(remote, n, exp_name, coll_name)
    if exp_obj is not None:
        print('Deleting experiment "{0}"...'.format(exp_obj.name))
        remote.delete_project(exp_obj)


def set_collection_resource(remote: BossRemote, params: dict) -> CollectionResource:
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


def delete_collection(remote: BossRemote, collection):
    coll_obj = None
    coll_name = None
    if isinstance(collection, CollectionResource):
        coll_obj = collection
        coll_name = collection.name
    elif isinstance(collection, str):
        coll_name = collection
        coll_obj = remote.get_project(CollectionResource(name=coll_name))
    if coll_name is not None:
        print('Deleting experiments of collection "{0}"...'.format(coll_name))
        exp_names = remote.list_experiments(coll_name)
        for n in exp_names:
            delete_experiment(remote, n, coll_name)
    if coll_obj is not None:
        print('Deleting collection "{0}"...'.format(coll_name))
        remote.delete_project(coll_obj)


def set_coordinate_frame_resource(remote: BossRemote, params: dict) -> CoordinateFrameResource:
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


def delete_coord_frame(remote: BossRemote, coord_frame):
    frame_obj = None
    # frame_name = None
    if isinstance(coord_frame, CoordinateFrameResource):
        frame_obj = coord_frame
        # frame_name = coord_frame.name
    elif isinstance(coord_frame, str):
        frame_name = coord_frame
        frame_obj = remote.get_project(CoordinateFrameResource(name=frame_name))
    if frame_obj is not None:
        print('Deleting coordinate frame "{0}"...'.format(frame_obj.name))
        remote.delete_project(frame_obj)


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
