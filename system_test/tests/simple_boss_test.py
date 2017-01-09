#!/usr/bin/env python3
# Copyright 2016 The Johns Hopkins University Applied Physics Laboratory
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http: //www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import systemtest
import time
from utils import boss_test_utils, numpy_utils, plot_utils


class SimpleBossTest(systemtest.SystemTest):
    """ System tests for the Boss API, testing different services.
    Intended to be easy method of testing cutout, tile, and image services.
    Properties (inherited):
        class_config    Static class dictionary (inherited from SystemTest)
        parameters      Parameters of the current test instance (inherited from SystemTest)
        result          Result of the current test instance (inherited from SystemTest)
    Attributes (inherited):

    """
    # Attributes:
    __collection_resource = None
    __coord_frame_resource = None
    __experiment_resource = None
    __channel_resource = None
    __remote_resource = None

    unit_size = [256, 256, 8, 1]
    step_size = [256, 256, 8, 1]
    steps = 1
    cache_hit = False
    cuboid_align = False
    resolution = 0
    delay = 0

    @property
    def channel_resource(self):
        return type(self).__channel_resource

    @property
    def remote_resource(self):
        return type(self).__remote_resource

    @property
    def experiment_resource(self):
        return type(self).__experiment_resource

    @property
    def collection_resource(self):
        return type(self).__collection_resource

    @classmethod
    def setUpClass(cls):
        """Use class configuration (+ defaults) to set up resources."""
        super(SimpleBossTest, cls).setUpClass()
        # Set up boss resources #
        remote = boss_test_utils.get_remote()
        # Default resources and configuration:
        config = {
            'collection':{'name': 'test_collection', 'delete':1},
            'coord_frame':{'name': 'test_frame', 'delete':1},
            'experiment':{'name': 'test_experiment', 'delete':1},
            'channel':{'name': 'test_channel', 'delete':1, 'datatype':'uint8'},
            'unit_size':[256, 256, 8, 1],
            'step_size':[256, 256, 8, 1],
            'steps':1
        }
        # Override certain defaults that appear in the class configuration:
        if 'collection' in cls._class_config:
            if 'name' in cls._class_config['collection']:
                config['collection']['name'] = cls._class_config['collection']['name']
            if 'delete' in cls._class_config['collection']:
                config['collection']['delete'] = cls._class_config['collection']['delete']
        if 'coord_frame' in cls._class_config:
            if 'name' in cls._class_config['coord_frame']:
                config['coord_frame']['name'] = cls._class_config['coord_frame']['name']
            if 'delete' in cls._class_config['coord_frame']:
                config['coord_frame']['delete'] = cls._class_config['coord_frame']['delete']
        if 'experiment' in cls._class_config:
            if 'name' in cls._class_config['experiment']:
                config['experiment']['name'] = cls._class_config['experiment']['name']
            if 'delete' in cls._class_config['experiment']:
                config['experiment']['delete'] = cls._class_config['experiment']['delete']
        if 'channel' in cls._class_config:
            if 'name' in cls._class_config['channel']:
                config['channel']['name'] = cls._class_config['channel']['name']
            if 'delete' in cls._class_config['channel']:
                config['channel']['delete'] = cls._class_config['channel']['delete']
        if 'unit_size' in cls._class_config:
            for i in range(0, min(4, len(cls._class_config['unit_size']))):
                config['unit_size'][i] = int(cls._class_config['unit_size'][i]) # x y z (t)
        if 'step_size' in cls._class_config:
            for i in range(0, min(4, len(cls._class_config['step_size']))):
                config['step_size'][i] = int(cls._class_config['step_size'][i])  # x y z (t)
        if 'steps' in cls._class_config:
            config['steps'] = int(cls._class_config['steps'])

        # We are not interested in any other variables; set everything else to default calculations
        x_sizes = [config['unit_size'][0] + (j * config['step_size'][0]) for j in range(0, config['steps'])]
        y_sizes = [config['unit_size'][1] + (j * config['step_size'][1]) for j in range(0, config['steps'])]
        z_sizes = [config['unit_size'][2] + (j * config['step_size'][2]) for j in range(0, config['steps'])]
        t_sizes = [config['unit_size'][3] + (j * config['step_size'][3]) for j in range(0, config['steps'])]
        config['coord_frame']['x_start'] = 0
        config['coord_frame']['y_start'] = 0
        config['coord_frame']['z_start'] = 0
        scale = 500
        config['coord_frame']['x_stop'] = scale * sum(x_sizes)
        config['coord_frame']['y_stop'] = scale * sum(y_sizes)
        config['coord_frame']['z_stop'] = scale * sum(z_sizes)
        # Create resource object for each resource
        cls.__collection_resource = boss_test_utils.set_collection_resource(
            remote, config['collection'])
        cls.__coord_frame_resource = boss_test_utils.set_coordinate_frame_resource(
            remote, config['coord_frame'])
        config['experiment']['num_time_samples'] = scale * sum(t_sizes)
        experiment = dict((k,v) for k,v in config['experiment'].items())
        experiment['collection_name'] = cls.__collection_resource.name
        experiment['coord_frame'] = cls.__coord_frame_resource.name
        cls.__experiment_resource = boss_test_utils.set_experiment_resource(
            remote, experiment)
        channel = dict((k,v) for k,v in config['channel'].items())
        channel['collection_name'] = cls.__collection_resource.name
        channel['experiment_name'] = cls.__experiment_resource.name
        cls.__channel_resource = boss_test_utils.set_channel_resource(
            remote, channel)
        cls.__remote_resource = remote
        # Drop anything else that was in the class config json
        cls._class_config = config


    # TODO: this may be incorrect
    @classmethod
    def tearDownClass(cls):
        """ Delete resources (in order) if specified in the class configuration """
        remote = boss_test_utils.get_remote()
        # config = cls._class_config
        try:
            boss_test_utils.delete_channel(remote, cls.__channel_resource)
        except:
            print('Failed to delete channel {0}'.format(cls.__channel_resource.name))
        try:
            boss_test_utils.delete_experiment(remote, cls.__experiment_resource)
        except:
            print('Failed to delete experiment {0}'.format(cls.__experiment_resource.name))
        try:
            boss_test_utils.delete_coord_frame(remote, cls.__coord_frame_resource)
        except:
            print('Failed to delete coordinate frame {0}'.format(cls.__coord_frame_resource.name))
        try:
            boss_test_utils.delete_collection(remote, cls.__collection_resource)
        except:
            print('Failed to delete collection {0}'.format(cls.__collection_resource.name))

        super(SimpleBossTest, cls).tearDownClass()
