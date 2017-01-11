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

import numpy, unittest, systemtest, time, requests
from utils import boss_test_utils, numpy_utils, plot_utils
from tests import sys_test_boss__base


class BossCutoutSystemTest(sys_test_boss__base.BossSystemTest):
    """ System tests for the Boss cutout service API, testing different write/read patterns.
    Properties (inherited):
        class_config    Static class dictionary (inherited from SystemTest)
        parameters      Parameters of the current test instance (inherited from SystemTest)
        result          Result of the current test instance (inherited from SystemTest)
    Attributes (inherited):
        _channel        Channel resource (inherited from BossSystemTest)
    """

    def validate_params(self, test_params: dict, is_constant_range=True):
        """ Validate the test input parameters """
        keys = ['x_range', 'y_range', 'z_range']
        if 'time_range' in test_params:
            keys.append('time_range')  # time_range is optional
        for key in keys:
            self.assertIn(key, test_params, 'Missing parameter {0}'.format(key))
            self.assertIsInstance(test_params[key], list, 'Improper type for {0}'.format(key))
            self.assertIn(len(test_params[key]), (2,3), 'Improper length for {0}'.format(key))
            vals = test_params[key]
            # self.assertLess(vals[0], vals[1], 'Improper {0}, start must be less than stop')
        # Parent method assigns self._channel:
        super(BossCutoutSystemTest, self).validate_params(test_params)
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
        x_vals = numpy_utils.array_range(params['x_range'])
        y_vals = numpy_utils.array_range(params['y_range'])
        z_vals = numpy_utils.array_range(params['z_range'])
        t_vals = numpy_utils.array_range(params['time_range']) if 'time_range' in params else None
        # translate = [] if not translate_axes else params['translate'].lower()
        coords_list = []
        # How many cutouts #
        num_cutouts = max(2, len(x_vals), len(y_vals), len(z_vals), 2 if not t_vals else len(t_vals)) - 1
        num_cutouts = max(2, len(x_vals), len(y_vals), len(z_vals), len(t_vals or [0, 0])) - 1
        # Get a tuple of (start, stop) coordinates along each axis

        def get_coords_from_array(vals, j):
            vi = vals[0] if len(vals) == 2 else (vals[min(j, len(vals) - 2) if translate_axes else 0])
            vj = vals[1] if len(vals) == 2 else vals[min(j + 1, len(vals) - 1)]
            return list([vi, vj]) if vi < vj else list([vj, vi])

        # Apply to the x, y, z, and t axes for each set of cutout coordinates
        for i in range(0, num_cutouts):
            xij = get_coords_from_array(x_vals, i)
            yij = get_coords_from_array(y_vals, i)
            zij = get_coords_from_array(z_vals, i)
            tij = get_coords_from_array(t_vals, i) if bool(t_vals) else None
            # Represent as a tuple of (start, stop) tuples, and append to a list #
            coords_list.append((xij, yij, zij, tij))
        # numpy_list = numpy.array(coords_list)
        return coords_list

    def do_cutout_behavior(self, write_or_read: str, coordinates_list: numpy.ndarray, resolution: int=0):
        """ Generic behavior for cutout tests. All of the tests use this pattern.
        """
        remote = boss_test_utils.get_remote()
        self.result['cutout_size'] = []
        self.result['duration'] = []
        data = -1
        # Loop through the different cutouts #
        if len(coordinates_list) > 1:
            if coordinates_list[0][0][0] != coordinates_list[1][0][0]:
                self.result['cutout_x'] = []
            if coordinates_list[0][1][0] != coordinates_list[1][1][0]:
                self.result['cutout_y'] = []
            if coordinates_list[0][2][0] != coordinates_list[1][2][0]:
                self.result['cutout_z'] = []
            if bool(coordinates_list[0][3]) and (coordinates_list[0][3][0] != coordinates_list[1][3][0]):
                self.result['cutout_t'] = []
        for x, y, z, t in coordinates_list:
            if 'cutout_x' in self.result:
                self.result['cutout_x'].append(int(x[0]))
            if 'cutout_y' in self.result:
                self.result['cutout_y'].append(int(y[0]))
            if 'cutout_z' in self.result:
                self.result['cutout_z'].append(int(z[0]))
            if 'cutout_t' in self.result:
                self.result['cutout_t'].append(int(t[0]))
            self.result['cutout_size'].append(int((x[1]-x[0])*(y[1]-y[0])*(z[1]-z[0])*(1 if not t else t[1]-t[0])))
            if write_or_read is 'write':
                data = numpy_utils.cuboid(x[1]-x[0], y[1]-y[0], z[1]-z[0],
                                          None if t is None else t[1]-t[0], self._channel.datatype)

                tick = time.time()
                remote.create_cutout(self._channel, resolution, x, y, z, data, t)
                self.result['duration'].append(time.time() - tick)
            else:
                tick = time.time()
                data = remote.get_cutout(self._channel, resolution, x, y, z, t)
                self.result['duration'].append(time.time() - tick)
        # if len(self.result['duration']) == 1:
        #     self.result['duration'] = self.result['duration'][0]
        return data

    # ##############
    # TEST FUNCTIONS
    # ##############

    @systemtest.systemtestmethod
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
        return

    @systemtest.systemtestmethod
    def cutout_read_test(self, params=None):
        """ System test case: Single download of a data cuboid. Record the duration for read operation to complete.
        """
        if not params:
            params = self.parameters
        self.validate_params(params)
        coordinates_list = self.get_coordinates_list(params)
        self.assertEqual(len(coordinates_list), 1, 'Expected fixed cutout dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        if ('initialize' in params) and (bool(params['initialize'])):
            self.do_cutout_behavior('write', coordinates_list, resolution)
            time.sleep(self.default_write_delay)
        self.do_cutout_behavior('read', coordinates_list, resolution)
        return

    @systemtest.systemtestmethod
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
        return

    @systemtest.systemtestmethod
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
        return

    @systemtest.systemtestmethod
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
        return

    @systemtest.systemtestmethod
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
        return

    @systemtest.systemtestmethod
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
        if ('initialize' in params) and (bool(params['initialize'])):
            self.do_cutout_behavior('write', coordinates_list, resolution)
            time.sleep(self.default_write_delay)
        self.do_cutout_behavior('read', coordinates_list, resolution)
        return

    @systemtest.systemtestmethod
    def cutout_write_throughput_size_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('write', coordinates_list, resolution)
        self.result[plot_utils.PLOT_KEY] = {
            'title': 'Write throughput, growing cutouts',
            'x': ''
        }
        return

    @systemtest.systemtestmethod
    def cutout_read_throughput_size_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing dimensions')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('read', coordinates_list, resolution)
        self.result[plot_utils.PLOT_KEY] = {
            'title': 'Read throughput, growing cutouts',
            'x': ''
        }
        return

    @systemtest.systemtestmethod
    def cutout_write_throughput_position_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params, True)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing coordinates')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('write', coordinates_list, resolution)
        self.result[plot_utils.PLOT_KEY] = {
            'title': 'Write throughput, moving cutouts',
            'x': ''
        }
        return

    @systemtest.systemtestmethod
    def cutout_read_throughput_position_test(self, params=None):
        """
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params, True)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing coordinates')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        self.do_cutout_behavior('read', coordinates_list, resolution)
        self.result[plot_utils.PLOT_KEY] = {
            'title': 'Read throughput, moving cutouts',
            'x': ''
        }
        return

    @systemtest.systemtestmethod
    def cutout_write_throughput_size_position_test(self, params=None):
        """
        Cutout test where cuboid selection increases in size and moves along the axis. If it increases in size along
        an axis, then it also moves in position along that axis. Uploads a cuboid from each set of coordinates
        and records the duration of the upload.
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing coordinates')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        ax = ['x_range', 'y_range', 'z_range', 'time_range']
        for d in range(0, len(ax)):
            # Determine if we should iterate on this axis
            if ax[d] in params and len(params[ax[d]]) >= 3:
                for c in range(1, len(coordinates_list)):
                    sz = abs(coordinates_list[c][d][1] - coordinates_list[c][d][0])
                    if coordinates_list[c][d][0] < coordinates_list[c][d][1]:
                        coordinates_list[c][d][0] = coordinates_list[c-1][d][1]
                        coordinates_list[c][d][1] = coordinates_list[c][d][0] + sz
                    else:
                        coordinates_list[c][d][1] = coordinates_list[c-1][d][0]
                        coordinates_list[c][d][0] = coordinates_list[c][d][1] - sz
        self.do_cutout_behavior('write', coordinates_list, resolution)
        self.result[plot_utils.PLOT_KEY] = {
            'title': 'Write throughput, growing and moving cutouts',
            'x': ''
        }
        return

    @systemtest.systemtestmethod
    def cutout_read_throughput_size_position_test(self, params=None):
        """
        Cutout test where cuboid selection increases in size and moves along the axis. If it increases in size along
        an axis, then it also moves in position along that axis. Downloads a cuboid from each set of coordinates
        and records the duration of the download.
        """
        if not params:
            params = self.parameters
        self.validate_params(params, is_constant_range=False)
        coordinates_list = self.get_coordinates_list(params)
        self.assertGreater(len(coordinates_list), 1, 'Given fixed cutout dimensions, expected changing coordinates')
        resolution = int(params['resolution']) if 'resolution' in params else 0
        ax = ['x_range', 'y_range', 'z_range', 'time_range']
        for d in range(0, len(ax)):
            # Determine if we should iterate on this axis
            if ax[d] in params and len(params[ax[d]]) >= 3:
                for c in range(1, len(coordinates_list)):
                    sz = abs(coordinates_list[c][d][1] - coordinates_list[c][d][0])
                    if coordinates_list[c][d][0] < coordinates_list[c][d][1]:
                        coordinates_list[c][d][0] = coordinates_list[c-1][d][1]
                        coordinates_list[c][d][1] = coordinates_list[c][d][0] + sz
                    else:
                        coordinates_list[c][d][1] = coordinates_list[c-1][d][0]
                        coordinates_list[c][d][0] = coordinates_list[c][d][1] - sz
        self.do_cutout_behavior('read', coordinates_list, resolution)
        self.result[plot_utils.PLOT_KEY] = {
            'title': 'Read throughput, growing and moving cutouts',
            'x': ''
        }
        return
