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
import requests
import time
import systemtest
from utils import boss_test_utils, numpy_utils, plot_utils
from tests import sys_test_boss__base


class BossImageSystemTest(sys_test_boss__base.BossSystemTest):
    """ System tests for the Boss image service API, testing different read patterns.
    Properties (inherited):
        class_config    Static class dictionary (inherited from SystemTest)
        parameters      Parameters of the current test instance (inherited from SystemTest)
        result          Result of the current test instance (inherited from SystemTest)
    Attributes (inherited):
        _channel        Channel resource (inherited from BossSystemTest)
    """
    def validate_params(self, test_params: dict, is_constant_range=True):
        """ Validate the test input parameters """
        self.assertIn('orientation', test_params, 'Missing parameter "orientation" (tile orientation)')
        fail_msg = 'Invalid "orientation" value (expects "xy" or "xz" or "yz" only)'
        self.assertIn(test_params['orientation'], ['yz', 'xz', 'xy'], fail_msg)
        if 'accept' in test_params:
            self.assertRegexpMatches(test_params['accept'], '^.*/.*$')
        keys = ['x_arg', 'y_arg', 'z_arg']
        if 't_index' in test_params:
            keys.append('t_index')  # t_index is optional
        for key in keys:
            is_dimension_flat = bool(key is 't_index') or \
                                bool(key is 'x_arg' and 'x' not in test_params['orientation']) or \
                                bool(key is 'y_arg' and 'y' not in test_params['orientation']) or \
                                bool(key is 'z_arg' and 'z' not in test_params['orientation'])
            if not isinstance(test_params[key], list):
                test_params[key] = list([test_params[key]])
            if is_dimension_flat:
                fail_msg = 'Improperly formatted {0}, expected single index'.format(key)
                self.assertIn(len(test_params[key]), (1, 3), fail_msg)
            else:
                self.assertIn(len(test_params[key]), (2, 3), 'Improper length for {0}'.format(key))
            vals = test_params[key]
            # if not is_dimension_flat:
            #     self.assertLess(vals[0], vals[1], 'Improper {0}, start must be less than stop')
        # Parent method assigns self._channel:
        super(BossImageSystemTest, self).validate_params(test_params)
        self.assertIsNotNone(self._channel)

    def tearDown(self):
        """ We may want to plot the results of tests that have multiple reads/writes """
        if 'throughput' in self.test_name:
            self.result[plot_utils.PLOT_KEY] = []
            self.result[plot_utils.PLOT_KEY].append({
                'x': 'image_size', 'xlabel': 'Image volume',
                'y': 'duration',
                'title': 'Image system test: {0}'.format(self.test_name)})
            for letter in ['x', 'y', 'z', 't']:
                key = 'image_{0}'.format(letter)
                if key in self.result:
                    self.result[plot_utils.PLOT_KEY].append({
                        'x': key, 'xlabel': 'Image {0}-axis start'.format(letter),
                        'y': 'duration',
                        'title': 'Image system test: {0}'.format(self.test_name)})
        super(BossImageSystemTest, self).tearDown()

    @staticmethod
    def get_coordinates_list(params: dict, translate_axes: bool=False):
        """ Use the axis ranges in params to calculate the extents of the image. Represent this as a tuple of
        (start, stop) tuples, like ((x0, x1), (y0, y1), (z0, z1), (time0, time1)). The time-axis tuple may be None if
        the test params do not contain 'time_range'. This function generates a list of these tuples-of-tuples, which
        enables it to 'schedule' a sequence of image reads or image writes.
        """
        x_vals = numpy_utils.array_range(params['x_arg'])
        y_vals = numpy_utils.array_range(params['y_arg'])
        z_vals = numpy_utils.array_range(params['z_arg'])
        t_vals = numpy_utils.array_range(params['t_index']) if 't_index' in params else None
        coords_list = []
        # How many images #
        # num_images = -1 + max(2, len(x_vals), len(y_vals), len(z_vals), (2 if t_vals is None else len(t_vals)))
        num_images = -1 + max(2, len(x_vals), len(y_vals), len(z_vals), len(t_vals or [0, 0]))
        # Get a tuple of (start, stop) coordinates OR (start) coordinate along each axis

        def get_coords_from_array(is_flat, vals, j):
            if is_flat:
                ci = vals[0] if len(vals) == 1 else (vals[min(j, len(vals) - 1) if translate_axes else 0])
                return (ci,)  # Return as tuple
            else:
                ci = vals[0] if len(vals) == 2 else (vals[min(j, len(vals) - 2) if translate_axes else 0])
                cj = vals[1] if len(vals) == 2 else vals[min(j + 1, len(vals) - 1)]
                return (ci, cj) if ci < cj else (cj, ci)

        # Apply to the x, y, z, and t axes for each set of image coordinates
        for i in range(0, num_images):
            xij = get_coords_from_array(bool('x' not in params['orientation']), x_vals, i)
            yij = get_coords_from_array(bool('y' not in params['orientation']), y_vals, i)
            zij = get_coords_from_array(bool('z' not in params['orientation']), z_vals, i)
            tij = get_coords_from_array(True, t_vals, i) if (t_vals is not None) else None
            # Represent as a tuple of (start, stop) tuples, and append to a list #
            coords_list.append((xij, yij, zij, tij))
        return coords_list

    def do_image_behavior(self, coordinates_list: numpy.ndarray, orientation: str, accept: str, resolution: int=0):
        """ Generic behavior for image tests. All of the tests use this pattern.
        """
        data = -1
        # try:
        if True:
            remote = boss_test_utils.get_remote()
            self.result['duration'] = []
            self.result['image_size'] = []
            # Loop through the different images #
            if len(coordinates_list) > 1:
                if coordinates_list[0][0][0] != coordinates_list[1][0][0]:
                    self.result['image_x'] = []
                if coordinates_list[0][1][0] != coordinates_list[1][1][0]:
                    self.result['image_y'] = []
                if coordinates_list[0][2][0] != coordinates_list[1][2][0]:
                    self.result['image_z'] = []
                if coordinates_list[0][3] is not None:
                    if coordinates_list[0][3][0] != coordinates_list[1][3][0]:
                        self.result['image_t'] = []
            for x, y, z, t in coordinates_list:
                x_str = '{0}:{1}'.format(x[0], x[1]) if 'x' in orientation else str(x[0])
                y_str = '{0}:{1}'.format(y[0], y[1]) if 'y' in orientation else str(y[0])
                z_str = '{0}:{1}'.format(z[0], z[1]) if 'z' in orientation else str(z[0])
                t_str = None if not t else str(t[0])
                if 'image_x' in self.result:
                    self.result['image_x'].append(int(x[0]))
                if 'image_y' in self.result:
                    self.result['image_y'].append(int(y[0]))
                if 'image_z' in self.result:
                    self.result['image_z'].append(int(z[0]))
                if 'image_t' in self.result:
                    self.result['image_t'].append(int(t[0]))
                self.result['image_size'].append(int((x[1]-x[0] if len(x) == 2 else 1) *
                                                 (y[1]-y[0] if len(y) == 2 else 1) *
                                                 (z[1]-z[0] if len(z) == 2 else 1)))
                self.result['url'] = "https://{0}/v{1}/image/{2}".format(
                    boss_test_utils.get_host(remote),
                    self._version,
                    "/".join([
                        self.class_config['collection']['name'],
                        self.class_config['experiment']['name'],
                        self._channel.name,
                        orientation,
                        str(resolution), x_str, y_str, z_str, str("" if not t_str else t_str)]))
                tick = time.time()
                obj = boss_test_utils.get_obj(remote, self.result['url'], accept)
                self.result['duration'].append(time.time() - tick)
                self.result['status_code'] = obj.status_code
                self.assertTrue(obj.ok, 'Bad request: {0}'.format(obj.reason))
                # self.assertNotIn(obj.status_code, [404, 500, 504], 'Received error status {0}'.format(obj.status_code))
            # if len(self.result['duration']) == 1:
            #     self.result['duration'] = self.result['duration'][0]
        # except Exception as e:
        #     self.result = {'error': str(e)}
        #     import sys
        #     tb = sys.exc_info()[2]
        #     print(e.with_traceback(tb))
        return data

    # ##############
    # TEST FUNCTIONS
    # ##############

    @systemtest.systemtestmethod
    def image_get_test(self, params=None):
        """ System test case: Single download of a image. Record the duration for read operation to complete.
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        coordinates_list = self.get_coordinates_list(params)
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_image_behavior(coordinates_list, orientation, format_accept, resolution)
        return
    
    @systemtest.systemtestmethod
    @unittest.expectedFailure
    def image_invalid_test(self, params=None):
        """ System test case: Single download of a image, expecting some invalid result.
        """
        if not params:
            params = self.parameters
        error = None
        try:
            self.image_get_test(params)
        except Exception as e:
            error = e
        finally:
            self.assertIsNotNone(error, 'Did not catch an error')
            if 'status' in params:
                if isinstance(error, requests.exceptions.HTTPError):
                    self.assertEqual(int(params['status']), error.response.status_code)
                else:
                    raise error
        return

    @systemtest.systemtestmethod
    def image_cache_hit_test(self, params=None):
        """ System test case:
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        coordinates_list = self.get_coordinates_list(params)
        coordinates_list += coordinates_list
        self.assertEqual(len(coordinates_list), 2, 'Expected fixed image coordinates')
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_image_behavior(coordinates_list, orientation, format_accept, resolution)
        return

    @systemtest.systemtestmethod
    def image_throughput_size_test(self, params=None):
        """ System test case:
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed image coords/size, expected changing value or values')
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_image_behavior(coordinates_list, orientation, format_accept, resolution)
        return
    
    @systemtest.systemtestmethod
    def image_throughput_position_test(self, params=None):
        """ System test case:
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params, True)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed image coords/size, expected changing value or values')
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_image_behavior(coordinates_list, orientation, format_accept, resolution)
        return
