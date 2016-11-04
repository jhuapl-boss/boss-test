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

import unittest
import numpy
import re
import systemtest
import requests
import time
from ndio.ndresource.boss.resource import *
from ndio.remote.boss.remote import Remote
from utils import boss_test_utils, plot_utils
from tests import sys_test_boss


class BossTileSystemTest(sys_test_boss.BossSystemTest):
    """ System tests for the Boss tile service API, testing different read patterns.
    Attributes:
        class_config    Static class dictionary (inherited from SystemTest)
        parameters      Parameters of the current test instance (inherited from SystemTest)
        result          Result of the current test instance (inherited from SystemTest)
        remote          Remote resource (inherited from BossSystemTest)
        channel         Channel resource (inherited from BossSystemTest)
    """
    
    def validate_params(self, test_params, is_constant_range=True):
        """ Validate the test input parameters """
        self.assertIn('orientation', test_params, 'Missing parameter "orientation" (tile orientation)')
        fail_msg = 'Invalid "orientation" value (expects "xy" or "xz" or "yz" only)'
        self.assertIn(test_params['orientation'], ['yz', 'xz', 'xy'], fail_msg)
        if 'accept' in test_params:
            self.assertRegexpMatches(test_params['accept'], '^.*/.*$')
        keys = ['x_idx', 'y_idx', 'z_idx', 'tile_size']
        if 't_idx' in test_params:
            keys.append('t_idx')  # t_idx is optional
        for key in keys:
            self.assertIn(key, test_params, 'Missing parameter {0}'.format(key))
            if isinstance(test_params[key], str):
                if is_constant_range:
                    fail_msg = 'Improperly formatted {0}, expected single "value"'.format(key)
                    self.assertRegexpMatches(test_params[key], '^[0-9]+?$', fail_msg)
                else:
                    fail_msg = 'Improperly formatted {0}, expected "index" or "start:stop:delta"'.format(key)
                    self.assertRegexpMatches(test_params[key], '^[0-9]+(:[0-9]+:[0-9]+)?$', fail_msg)
            elif not isinstance(test_params[key], int):
                self.assertIsInstance(test_params[key], list, 'Improper type for {0}'.format(key))
                self.assertIn(len(test_params[key]), (1,3), 'Improper length for {0}'.format(key))
        # Parent method assigns self._channel:
        super(BossTileSystemTest, self).validate_params(test_params)
        self.assertIsNotNone(self._remote)
        self.assertIsNotNone(self._channel)

    def tearDown(self):
        """ We may want to plot the results of tests that have multiple reads """
        if 'throughput' in self.test_name:
            self.result[plot_utils.PLOT_KEY] = []
            for letter in ['x', 'y', 'z', 't', 'size']:
                key = 'tile_{0}'.format(letter)
                if key in self.result:
                    self.result[plot_utils.PLOT_KEY].append({
                        'x': key, 'xlabel': 'Tile {0} '.format(letter),
                        'y': 'duration',
                        'title': 'Tile system test: {0}'.format(self.test_name)})
        super(BossTileSystemTest, self).tearDown()

    @staticmethod
    def get_index_list(params:dict):
        """ Parse the range parameters """
        x_idxs = boss_test_utils.parse_param_list(params, 'x_idx', False)
        y_idxs = boss_test_utils.parse_param_list(params, 'y_idx', False)
        z_idxs = boss_test_utils.parse_param_list(params, 'z_idx', False)
        t_idxs = boss_test_utils.parse_param_list(params, 't_idx', False) if 't_idx' in params else None
        tile_sizes = boss_test_utils.parse_param_list(params, 'tile_size', False)
        idxs_list = []
        # How many tiles? #
        num_tiles = max(1, len(x_idxs), len(y_idxs), len(z_idxs), 1 if not t_idxs else len(t_idxs), len(tile_sizes))
        for i in range(0, num_tiles):
            xi = x_idxs[min(i, len(x_idxs)-1)]
            yi = y_idxs[min(i, len(y_idxs)-1)]
            zi = z_idxs[min(i, len(z_idxs)-1)]
            ti = None if not bool(t_idxs) else t_idxs[min(i, len(t_idxs)-1)]
            tile_size = tile_sizes[min(i, len(tile_sizes)-1)]
            idxs_list.append((xi, yi, zi, ti if t_idxs else None, tile_size))
        return idxs_list

    def do_tile_behavior(self, index_list:list, orientation, accept:str, resolution=0):
        """ Generic behavior for tile tests. All of the tests use this pattern.
        """
        self.result['duration'] = list([])
        obj = None
        if len(index_list) > 1:
            if index_list[0][0] != index_list[1][0]: self.result['tile_x'] = []
            if index_list[0][1] != index_list[1][1]: self.result['tile_y'] = []
            if index_list[0][2] != index_list[1][2]: self.result['tile_z'] = []
            if index_list[0][3] is not None:
                if index_list[0][3] != index_list[1][3]: self.result['tile_t'] = []
            if index_list[0][4] != index_list[1][4]: self.result['tile_size'] = []
        for x_idx, y_idx, z_idx, t_idx, tile_size in index_list:
            if 'tile_x' in self.result: self.result['tile_x'].append(x_idx)
            if 'tile_y' in self.result: self.result['tile_y'].append(y_idx)
            if 'tile_z' in self.result: self.result['tile_z'].append(z_idx)
            if 'tile_t' in self.result: self.result['tile_t'].append(t_idx)
            if 'tile_size' in self.result: self.result['tile_size'].append(tile_size)
            self.result['url'] = "https://{0}/v{1}/tile/{2}".format(
                self.parser_args.domain, self._version,
                "/".join([
                    self.class_config['collection']['name'],
                    self.class_config['experiment']['name'],
                    self._channel.name,
                    orientation,
                    str(tile_size),
                    str(resolution), str(x_idx), str(y_idx), str(z_idx), str("" if not t_idx else t_idx)]))
            tick = time.time()
            obj = boss_test_utils.get_obj(self._remote, self.result['url'], accept)
            self.result['duration'].append(time.time() - tick)
            self.result['status_code'] = obj.status_code
            self.assertTrue(obj.ok, 'Bad request: {0}'.format(obj.reason))
            # self.assertNotIn(obj.status_code, [404, 500, 504], 'Received error status {0}'.format(obj.status_code))
        if len(self.result['duration']) == 1:
            self.result['duration'] = self.result['duration'][0]
        return obj

    def tile_get_test(self, params=None):
        """ System test case: Single download of a tile. Record the duration for read operation to complete.
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        index_list = self.get_index_list(params)
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_tile_behavior(index_list, orientation, format_accept, resolution)
        pass

    @unittest.expectedFailure
    def tile_invalid_test(self, params=None):
        """ System test case: Single download of a tile, expecting some invalid result.
        """
        if not params:
            params = self.parameters
        error = None
        try:
            self.tile_get_test(params)
        except Exception as e:
            error = e
        finally:
            self.assertIsNotNone(error, 'Did not catch an error')
            if 'status' in params:
                if isinstance(error, requests.exceptions.HTTPError):
                    self.assertEqual(int(params['status']), error.response.status_code)
                else:
                    raise error
        pass

    def tile_cache_hit_test(self, params=None):
        """ System test case:
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        index_list = self.get_index_list(params)
        index_list += index_list
        self.assertEqual(len(index_list), 2, 'Expected fixed tile indices')
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_tile_behavior(index_list, orientation, format_accept, resolution)
        pass

    def tile_throughput_size_test(self, params=None):
        """ System test case:
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        index_list = self.get_index_list(params)
        self.assertGreater(len(index_list), 1, 'Given fixed tile position, expected changing value or values')
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_tile_behavior(index_list, orientation, format_accept, resolution)
        pass

    def tile_throughput_cache_miss_test(self, params=None):
        """ System test case:
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        index_list = self.get_index_list(params)
        self.assertGreater(len(index_list), 1, 'Given fixed tile position, expected changing value or values')
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_tile_behavior(index_list, orientation, format_accept, resolution)
        pass