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

# import inspect
import unittest
import numpy
import re
import systemtest
import requests
import time
from utils import boss_test_utils


class BossSystemTest(systemtest.SystemTest):

    # Protected attributes:
    _channel = None     # Each test uses either the "default" (initial) channel or a new channel
    _remote = None      # Always have a new remote for every test
    _version = None      # Boss version

    # Channel defined from initial class configuration
    __default_channel = None
    @property
    def default_channel(self):
        return type(self).__default_channel

    @default_channel.setter
    def default_channel(self, value):
        type(self).__default_channel = value

    # Default time (in seconds) to wait after writing to the channel #
    __write_delay = float(5.0)
    @property
    def default_write_delay(self):
        return type(self).__write_delay

    @classmethod
    def setUpClass(cls):
        """ Set up the default channel as specified in the class configuration """
        test_config = cls._class_config
        if bool(test_config):
            # Set up default channel #
            boss_test_utils.setup_boss_resources(test_config)
            if 'channel' in test_config:
                remote = boss_test_utils.new_remote()
                cls.default_channel = boss_test_utils.get_channel(remote, test_config['channel'], test_config)

    def setUp(self):
        """ Set up a new remote for the current test """
        super(BossSystemTest, self).setUp()
        if 'version' in self.class_config:
            self._version = self.class_config['version']
        else:
            self._version = self.parser_args.version
        self._remote = boss_test_utils.new_remote()

    def validate_params(self, test_params=None):
        """ Call this at the start of the system test method """
        if test_params is not None:
            if 'channel' in test_params:
                self._channel = boss_test_utils.get_channel(self._remote, test_params['channel'], self.class_config)
                time.sleep(self.default_write_delay)
            else:
                self._channel = self.default_channel

    # def tearDown(self):
    #     if self._channel is not type(self).__default_channel:
    #         boss_test_utils.delete_channel(self._remote, self._channel)
    #     super(BossSystemTest, self).tearDown()
