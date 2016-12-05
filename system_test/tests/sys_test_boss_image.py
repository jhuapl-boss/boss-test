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
from utils import boss_test_utils, plot_utils
from tests import sys_test_boss


class BossImageSystemTest(sys_test_boss.BossSystemTest):
    """ System tests for the Boss image service API, testing different read patterns.
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
        keys = ['x_arg', 'y_arg', 'z_arg']
        if 't_index' in test_params:
            keys.append('t_index')  # t_index is optional
        for key in keys:
            is_dimension_flat = bool(key is 't_index') or \
                                bool(key is 'x_arg' and 'x' not in test_params['orientation']) or \
                                bool(key is 'y_arg' and 'y' not in test_params['orientation']) or \
                                bool(key is 'z_arg' and 'z' not in test_params['orientation'])
            # if isinstance(test_params[key], str):
            #     if is_constant_range and is_dimension_flat:
            #         fail_msg = 'Improperly formatted {0}, expected single "index"'.format(key)
            #         self.assertRegexpMatches(test_params[key], '^[0-9]+$', fail_msg)
            #     elif is_constant_range:
            #         fail_msg = 'Improperly formatted {0}, expected "start:stop"'.format(key)
            #         self.assertRegexpMatches(test_params[key], '^[0-9]+:[0-9]+?$', fail_msg)
            #     else:
            #         fail_msg = 'Improperly formatted {0}, expected "start:stop"" or "start:stop:delta"'.format(key)
            #         self.assertRegexpMatches(test_params[key], '^[0-9]+:[0-9]+(:[0-9]+)?$', fail_msg)
            #     vals = [int(x) for x in re.split(':', test_params[key])]
            # else:
            if not isinstance(test_params[key],list): test_params[key] = list([test_params[key]])
            if is_dimension_flat:
                fail_msg = 'Improperly formatted {0}, expected single index'.format(key)
                self.assertIn(len(test_params[key]), (1,3), fail_msg)
            else:
                self.assertIn(len(test_params[key]), (2,3), 'Improper length for {0}'.format(key))
            vals = test_params[key]
            if not is_dimension_flat:
                self.assertLess(vals[0], vals[1], 'Improper {0}, start must be less than stop')
        # Parent method assigns self._channel:
        super(BossImageSystemTest, self).validate_params(test_params)
        self.assertIsNotNone(self._remote)
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
        x_vals = boss_test_utils.parse_param_list(params, 'x_arg', False)
        y_vals = boss_test_utils.parse_param_list(params, 'y_arg', False)
        z_vals = boss_test_utils.parse_param_list(params, 'z_arg', False)
        t_vals = boss_test_utils.parse_param_list(params, 't_index', False) if 't_index' in params else None
        # translate = [] if not translate_axes else params['translate'].lower()
        dimlist = []
        # How many images #
        num_images = max(2, len(x_vals), len(y_vals), len(z_vals), 2 if not t_vals else len(t_vals)) - 1
        # Get a tuple of (start, stop) coordinates OR (start) coordinate along each axis
        def get_coord_from_array(is_flat, vals, i, letter_key):
            if is_flat:
                # ci = vals[0] if len(vals) == 1 else (vals[min(i, len(vals) - 1) if letter_key in translate else 0])
                ci = vals[0] if len(vals) == 1 else (vals[min(i, len(vals) - 1) if translate_axes else 0])
                return (ci,)
            else:
                # ci = vals[0] if len(vals) == 2 else (vals[min(i, len(vals) - 2) if letter_key in translate else 0])
                ci = vals[0] if len(vals) == 2 else (vals[min(i, len(vals) - 2) if translate_axes else 0])
                cj = vals[1] if len(vals) == 2 else vals[min(i + 1, len(vals) - 1)]
                return (ci, cj) if ci < cj else (cj, ci)
        # Apply to the x, y, z, and t axes for each set of image coordinates
        for i in range(0, num_images):
            xij = get_coord_from_array(bool('x' not in params['orientation']), x_vals, i, 'x')
            yij = get_coord_from_array(bool('y' not in params['orientation']), y_vals, i, 'y')
            zij = get_coord_from_array(bool('z' not in params['orientation']), z_vals, i, 'z')
            tij = get_coord_from_array(True, t_vals, i, 't') if bool(t_vals) else None
            # Represent as a tuple of (start, stop) tuples, and append to a list #
            dimlist.append((xij, yij, zij, tij))
        return dimlist

    def do_image_behavior(self, coordinates_list:list, orientation:str, accept:str, resolution=0):
        """ Generic behavior for image tests. All of the tests use this pattern.
        """
        self.result['duration'] = list([])
        self.result['image_size'] = list([])
        data = -1
        # Loop through the different images #
        if len(coordinates_list) > 1:
            if coordinates_list[0][0][0] != coordinates_list[1][0][0]: self.result['image_x'] = []
            if coordinates_list[0][1][0] != coordinates_list[1][1][0]: self.result['image_y'] = []
            if coordinates_list[0][2][0] != coordinates_list[1][2][0]: self.result['image_z'] = []
            if coordinates_list[0][3] is not None:
                if coordinates_list[0][3][0] != coordinates_list[1][3][0]: self.result['image_t'] = []
        for x, y, z, t in coordinates_list:
            x_str = '{0}:{1}'.format(x[0], x[1]) if 'x' in orientation else str(x[0])
            y_str = '{0}:{1}'.format(y[0], y[1]) if 'y' in orientation else str(y[0])
            z_str = '{0}:{1}'.format(z[0], z[1]) if 'z' in orientation else str(z[0])
            t_str = None if not t else str(t[0])
            if 'image_x' in self.result: self.result['image_x'].append(x[0])
            if 'image_y' in self.result: self.result['image_y'].append(y[0])
            if 'image_z' in self.result: self.result['image_z'].append(z[0])
            if 'image_t' in self.result: self.result['image_t'].append(t[0])
            self.result['image_size'].append((x[1]-x[0] if len(x) == 2 else 1)*
                                             (y[1]-y[0] if len(y) == 2 else 1)*
                                             (z[1]-z[0] if len(z) == 2 else 1))
            self.result['url'] = "https://{0}/v{1}/image/{2}".format(
                self.parser_args.domain, self._version,
                "/".join([
                    self.class_config['collection']['name'],
                    self.class_config['experiment']['name'],
                    self._channel.name,
                    orientation,
                    str(resolution), x_str, y_str, z_str, str("" if not t_str else t_str)]))
            tick = time.time()
            obj = boss_test_utils.get_obj(self._remote, self.result['url'], accept)
            self.result['duration'].append(time.time() - tick)
            self.result['status_code'] = obj.status_code
            self.assertTrue(obj.ok, 'Bad request: {0}'.format(obj.reason))
            # self.assertNotIn(obj.status_code, [404, 500, 504], 'Received error status {0}'.format(obj.status_code))
        if len(self.result['duration']) == 1:
            self.result['duration'] = self.result['duration'][0]
        return data

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
        pass

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
        pass

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
        pass

    def image_throughput_size_test(self, params=None):
        """ System test case:
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed image position/size, expected changing value or values')
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_image_behavior(coordinates_list, orientation, format_accept, resolution)
        pass

    def image_throughput_cache_miss_test(self, params=None):
        """ System test case:
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params, True)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed image position/size, expected changing value or values')
        orientation = str(self.parameters['orientation'])
        format_accept = str(self.parameters['accept']) if 'accept' in params else 'image/png'
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_image_behavior(coordinates_list, orientation, format_accept, resolution)
        pass
