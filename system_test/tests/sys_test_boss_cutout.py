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

import numpy, re, unittest, systemtest, time, requests
from ndio.ndresource.boss.resource import *
from ndio.remote.boss.remote import Remote
from utils import boss_test_utils, plot_utils
from tests import sys_test_boss


class BossCutoutSystemTest(sys_test_boss.BossSystemTest):
    """ System tests for the Boss cutout service API, testing different write/read patterns.
    Attributes:
        class_config    Static class dictionary (inherited from SystemTest)
        parameters      Parameters of the current test instance (inherited from SystemTest)
        result          Result of the current test instance (inherited from SystemTest)
        remote          Remote resource (inherited from BossSystemTest)
        channel         Channel resource (inherited from BossSystemTest)
    """

    def validate_params(self, test_params, is_constant_range=True):
        """ Validate the test input parameters """
        keys = ['x_range', 'y_range', 'z_range']
        if 'time_range' in test_params:
            keys.append('time_range')  # time_range is optional
        for key in keys:
            self.assertIn(key, test_params, 'Missing parameter {0}'.format(key))
            if isinstance(test_params[key], str):
                if is_constant_range:
                    fail_msg = 'Improperly formatted {0}, expected "start:stop"'.format(key)
                    self.assertRegexpMatches(test_params[key], '^[0-9]+:[0-9]+?$', fail_msg)
                else:
                    fail_msg = 'Improperly formatted {0}, expected "start:stop"" or "start:stop:delta"'.format(key)
                    self.assertRegexpMatches(test_params[key], '^[0-9]+:[0-9]+(:[0-9]+)?$', fail_msg)
                vals = [int(x) for x in re.split(':', test_params[key])]
            else:
                self.assertIsInstance(test_params[key], list, 'Improper type for {0}'.format(key))
                self.assertIn(len(test_params[key]), (2,3), 'Improper length for {0}'.format(key))
                vals = test_params[key]
            self.assertLess(vals[0], vals[1], 'Improperly formatted {0}, "start"" must be less than "stop"')
        # Parent method BossSystemTest.setUp assigns self._remote and self._channel:
        super(BossCutoutSystemTest, self).validate_params(test_params)
        self.assertIsNotNone(self._remote)
        self.assertIsNotNone(self._channel)

    def tearDown(self):
        """ We may want to plot the results of tests that have multiple reads/writes """
        if 'throughput' in self.test_name:
            self.result[plot_utils.PLOT_KEY] = []
            self.result[plot_utils.PLOT_KEY].append({
                'x': 'cutout_size', 'xlabel': 'Cutout volume',
                'y': 'duration',
                'title': 'Cutout system test: {0}'.format(self.test_name)})
            for letter in ['x', 'y', 'z', 't']:
                key = 'cutout_{0}'.format(letter)
                if key in self.result:
                    self.result[plot_utils.PLOT_KEY].append({
                        'x': key, 'xlabel': 'Cutout {0}-axis start'.format(letter),
                        'y': 'duration',
                        'title': 'Cutout system test: {0}'.format(self.test_name)})
        super(BossCutoutSystemTest, self).tearDown()

    @staticmethod
    def get_coordinates_list(params: dict, translate_axes: bool=False):
        """ Use the axis ranges in params to calculate the extents of the cutout. Represent this as a tuple of
        (start, stop) tuples, like ((x0, x1), (y0, y1), (z0, z1), (time0, time1)). The time-axis tuple may be None if
        the test params do not contain 'time_range'. This function generates a list of these tuples-of-tuples, which
        enables it to 'schedule' a sequence of cutout reads or cutout writes.
        """
        x_vals = boss_test_utils.parse_param_list(params, 'x_range', False)
        y_vals = boss_test_utils.parse_param_list(params, 'y_range', False)
        z_vals = boss_test_utils.parse_param_list(params, 'z_range', False)
        t_vals = boss_test_utils.parse_param_list(params, 'time_range', False) if 'time_range' in params else None
        translate = [] if not translate_axes else params['translate'].lower()
        dimlist = []
        # How many cutouts #
        num_cutouts = max(2, len(x_vals), len(y_vals), len(z_vals), 2 if not t_vals else len(t_vals)) - 1
        # Get a tuple of (start, stop) coordinates along each axis
        def get_coord_from_array(vals, i, letter_key):
            vi = vals[0] if len(vals) == 2 else (vals[min(i, len(vals) - 2) if translate_axes else 0])
            # vi = vals[0] if len(vals) == 2 else (vals[min(i, len(vals) - 2) if letter_key in translate else 0])
            vj = vals[1] if len(vals) == 2 else vals[min(i + 1, len(vals) - 1)]
            return (vi, vj) if vi < vj else (vj, vi)
        # Apply to the x, y, z, and t axes for each set of cutout coordinates
        for i in range(0, num_cutouts):
            xij = get_coord_from_array(x_vals, i, 'x')
            yij = get_coord_from_array(y_vals, i, 'y')
            zij = get_coord_from_array(z_vals, i, 'z')
            tij = get_coord_from_array(t_vals, i, 't') if bool(t_vals) else None
            # Represent as a tuple of (start, stop) tuples, and append to a list #
            dimlist.append((xij, yij, zij, tij))
        return dimlist

    def do_cutout_behavior(self, write_or_read:str, coordinates_list:list, resolution=0):
        """ Generic behavior for cutout tests. All of the tests use this pattern.
        """
        self.result['duration'] = list([])
        self.result['cutout_size'] = list([])
        data = -1
        # Loop through the different cutouts #
        if len(coordinates_list) > 1:
            if coordinates_list[0][0][0] != coordinates_list[1][0][0]: self.result['cutout_x'] = []
            if coordinates_list[0][1][0] != coordinates_list[1][1][0]: self.result['cutout_y'] = []
            if coordinates_list[0][2][0] != coordinates_list[1][2][0]: self.result['cutout_z'] = []
            if coordinates_list[0][3] is not None:
                if coordinates_list[0][3][0] != coordinates_list[1][3][0]: self.result['cutout_t'] = []
        for x, y, z, t in coordinates_list:
            x_str = '{0}:{1}'.format(x[0], x[1])
            y_str = '{0}:{1}'.format(y[0], y[1])
            z_str = '{0}:{1}'.format(z[0], z[1])
            t_str = None if not t else '{0}:{1}'.format(t[0], t[1])
            if 'cutout_x' in self.result: self.result['cutout_x'].append(x[0])
            if 'cutout_y' in self.result: self.result['cutout_y'].append(y[0])
            if 'cutout_z' in self.result: self.result['cutout_z'].append(z[0])
            if 'cutout_t' in self.result: self.result['cutout_t'].append(t[0])
            self.result['cutout_size'].append((x[1]-x[0])*(y[1]-y[0])*(z[1]-z[0])*max(1,1 if not t else t[1]-t[0]))
            if write_or_read is 'write':
                data = boss_test_utils.cuboid(self._channel.datatype,
                                              x[1]-x[0], y[1]-y[0], z[1]-z[0], t[1]-t[0] if t else 0)
                tick = time.time()
                self._remote.cutout_create(self._channel, resolution,
                                     data=data, x_range=x_str, y_range=y_str, z_range=z_str, time_range=t_str)
                self.result['duration'].append(time.time() - tick)
            else:
                tick = time.time()
                data = self._remote.cutout_get(self._channel, resolution,
                                     x_range=x_str, y_range=y_str, z_range=z_str, time_range=t_str)
                self.result['duration'].append(time.time() - tick)
        if len(self.result['duration']) == 1: self.result['duration'] = self.result['duration'][0]
        return data

    def cutout_write_test(self, params=None):
        """ System test case: Single upload of a data cuboid. Record the duration for write operation to complete.
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        coordinates_list = self.get_coordinates_list(params)
        self.assertEqual(len(coordinates_list), 1, 'Expected fixed cutout dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('write', coordinates_list, resolution)
        pass

    def cutout_read_test(self, params=None):
        """ System test case: Single download of a data cuboid. Record the duration for read operation to complete.
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        coordinates_list = self.get_coordinates_list(params)
        self.assertEqual(len(coordinates_list), 1, 'Expected fixed cutout dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('read', coordinates_list, resolution)
        pass

    @unittest.expectedFailure
    def cutout_write_invalid_test(self, params=None):
        """ System test case: Single upload of a data cuboid, expecting some invalid parameter configuration.
        """
        if not params:
            params = self.parameters
        error = None
        try:
            self.cutout_write_test(params)
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

    @unittest.expectedFailure
    def cutout_read_invalid_test(self, params=None):
        """ System test case: Single download of a data cuboid, expecting some invalid result.
        """
        if not params:
            params = self.parameters
        error = None
        try:
            self.cutout_read_test(params)
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

    def cutout_match_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        coordinates_list = self.get_coordinates_list(params)
        self.assertEqual(len(coordinates_list), 1, 'Expected fixed cutout dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        data_write = self.do_cutout_behavior('write', coordinates_list, resolution)
        time.sleep(self.default_write_delay)
        data_read = self.do_cutout_behavior('read', coordinates_list, resolution)
        numpy.testing.assert_array_equal(data_write, data_read, 'Mismatched uploaded and downloaded data.', True)
        pass

    def cutout_write_cache_hit_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        coordinates_list = self.get_coordinates_list(params)
        coordinates_list += coordinates_list
        self.assertEqual(len(coordinates_list), 2, 'Expected fixed cutout dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('write', coordinates_list, resolution)
        pass

    def cutout_read_cache_hit_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        coordinates_list = self.get_coordinates_list(params)
        coordinates_list += coordinates_list
        self.assertEqual(len(coordinates_list), 2, 'Expected fixed cutout dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('read', coordinates_list, resolution)
        pass

    def cutout_write_throughput_size_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params)
        coordinates_list += coordinates_list
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('write', coordinates_list, resolution)
        pass

    def cutout_read_throughput_size_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params)
        coordinates_list += coordinates_list
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('read', coordinates_list, resolution)
        pass

    def cutout_write_throughput_cache_miss_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        # self.assertIn('translate', params)
        # self.assertIsInstance(params['translate'], str)
        coordinates_list = self.get_coordinates_list(params, True)
        coordinates_list += coordinates_list
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing coordinates')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('write', coordinates_list, resolution)
        pass

    def cutout_read_throughput_cache_miss_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        # self.assertIn('translate', params)
        # self.assertIsInstance(params['translate'], str)
        coordinates_list = self.get_coordinates_list(params, True)
        coordinates_list += coordinates_list
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing coordinates')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('read', coordinates_list, resolution)
        pass
