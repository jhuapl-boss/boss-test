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


import systemtest
import time
from utils import boss_test_utils


class BossSystemTest(systemtest.SystemTest):

    # Protected attributes:
    _channel = None     # Each test uses either the "default" (initial) channel or a new channel
    _version = None      # Boss version

    # Class attributes:
    __collection = None
    __coordinate_frame = None
    __experiment = None
    __default_channel = None
    __write_delay = float(5.0)  # Default time (in seconds) to wait after writing to the channel #

    @property
    def default_channel(self):
        return type(self).__default_channel

    @property
    def default_write_delay(self):
        return type(self).__write_delay

    @classmethod
    def setUpClass(cls):
        """ Set up the default channel as specified in the class configuration """
        if bool(cls._class_config):
            # Set up boss resources #
            remote = boss_test_utils.get_remote()
            cls.__collection = boss_test_utils.get_collection_resource(
                remote,
                cls._class_config['collection'])
            cls.__coordinate_frame = boss_test_utils.get_coordinate_frame_resource(
                remote,
                cls._class_config['coordinate_frame'])
            cls._class_config['experiment']['collection_name'] = cls.__collection.name
            cls._class_config['experiment']['coord_frame'] = cls.__coordinate_frame.name
            cls.___experiment = boss_test_utils.get_experiment_resource(
                remote,
                cls._class_config['experiment'])
            cls._class_config['channel']['collection_name'] = cls.__collection.name
            cls._class_config['channel']['experiment_name'] = cls.___experiment.name
            cls.__default_channel = boss_test_utils.get_channel_resource(
                remote,
                cls._class_config['channel'])

    def setUp(self):
        """Called before a single test begins. Set up a new remote for the current test """
        super(BossSystemTest, self).setUp()
        if 'version' in self.class_config:
            self._version = self.class_config['version']
        else:
            self._version = self.parser_args.version

    def validate_params(self, test_params=None, *args, **kwargs):
        """Call this at the start of the system test method """
        if test_params is not None:
            if 'channel' in test_params:
                remote = boss_test_utils.get_remote()
                test_params['channel']['collection_name'] = self.default_channel.collection_name
                test_params['channel']['experiment_name'] = self.default_channel.experiment_name
                self._channel = boss_test_utils.get_channel_resource(
                    remote,
                    test_params['channel'])
                time.sleep(self.default_write_delay)
            else:
                self._channel = self.default_channel

    def tearDown(self):
        """Called after a single test completes"""
        super(BossSystemTest, self).tearDown()
        if ('delete' in self.parameters) and bool(self.parameters['delete']) and \
                (self._channel is not self.default_channel):
            remote = boss_test_utils.get_remote()
            remote.delete_project(self._channel)

    @classmethod
    def tearDownClass(cls):
        """ Delete resources (in order) if specified in the class configuration """
        _config, remote = cls._class_config, boss_test_utils.get_remote()

        def delete_resource(resource):
            try:
                if bool(resource):
                    remote.delete_project(resource)
                return None
            except:
                return resource
        # Delete is TRUE by default
        if ('channel' not in _config) or ('delete' not in _config['channel']) or bool(_config['channel']['delete']):
            cls.__default_channel = delete_resource(cls.__default_channel)
        if ('delete' not in _config['experiment']) or bool(_config['experiment']['delete']):
            cls.__default_channel = delete_resource(cls.__default_channel)
            cls.__experiment = delete_resource(cls.__experiment)
        if ('delete' not in _config['coordinate_frame']) or bool(_config['coordinate_frame']['delete']):
            cls.__default_channel = delete_resource(cls.__default_channel)
            cls.__experiment = delete_resource(cls.__experiment)
            cls.__coordinate_frame = delete_resource(cls.__coordinate_frame)
        if ('delete' not in _config['collection']) or bool(_config['collection']['delete']):
            cls.__default_channel = delete_resource(cls.__default_channel)
            cls.__experiment = delete_resource(cls.__experiment)
            cls.__collection = delete_resource(cls.__collection)
        super(BossSystemTest, cls).tearDownClass()

