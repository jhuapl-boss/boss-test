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
import unittest
import requests.exceptions
import time
from utils import boss_test_utils, numpy_utils, plot_utils
from tests import simple_boss_test


class SimpleBossCutoutTest(simple_boss_test.SimpleBossTest):
    """ System tests for the Boss cutout service API, testing different write/read patterns.
    Intended as a simplified version of sys_test_boss_cutout.BossCutoutSystemTest.
    Properties (inherited):
        class_config    Static class dictionary (inherited from SystemTest)
        parameters      Parameters of the current test instance (inherited from SystemTest)
        result          Result of the current test instance (inherited from SystemTest)
    Attributes (inherited):
        __collection_resource = None
        __coord_frame_resource = None
        __experiment_resource = None
        __channel_resource = None

    """
    # unit_size = [512, 512, 16, 1]
    # step_size = [512, 512, 16, 1]
    # steps = 1
    # cache_hit = False
    # cuboid_align = False

    # default_unit_size = [256, 256, 8, 1]
    # default_step_size = [256, 256, 8, 0]
    # default_steps = 10

    def validate_params(self, test_params: dict):
        """ Validate the test input parameters. Replace class attributes if any are given. """
        # Defaults
        self.unit_size = self.class_config['unit_size']
        if 'unit_size' in test_params:
            self.assertIsInstance(test_params['unit_size'], list)
            self.assertIn(len(test_params['unit_size']), [3, 4]) # t size is optional
            for i in range(0, min(4, len(test_params['unit_size']))):
                self.unit_size[i] = int(test_params['unit_size'][i]) # x y z (t)
        self.step_size = self.unit_size
        if 'step_size' in self.class_config:
            self.step_size = self.class_config['step_size']
        if 'step_size' in test_params:
            self.assertIsInstance(test_params['step_size'], list)
            self.assertIn(len(test_params['step_size']), [3, 4]) # t size is optional
            for i in range(0, min(4, len(test_params['step_size']))):
                self.step_size[i] = int(test_params['step_size'][i]) # x y z (t)
        self.steps = int(self.class_config['steps'])
        if 'steps' in test_params:
            self.assertIsInstance(test_params['steps'], int)
            self.assertGreaterEqual(int(test_params['steps']), 1)
            self.steps = int(test_params['steps'])
        if 'cache_hit' in test_params:
            self.assertIsInstance(bool(test_params['cache_hit']), bool)
            self.cache_hit = bool(test_params['cache_hit'])
        if 'cuboid_align' in test_params:
            self.assertIsInstance(bool(test_params['cuboid_align']), bool)
            self.cuboid_align = bool(test_params['cuboid_align'])
        if 'delay' in test_params:
            self.assertIsInstance(test_params['delay'],[int, float])
            self.delay = float(test_params['delay'])
        # Filter test parameters:
        return {
            'unit_size': self.unit_size,
            'step_size': self.step_size,
            'steps': self.steps,
            'cache_hit': self.cache_hit,
            'cuboid_align': self.cuboid_align,
            'delay': self.delay
        }

    def tearDown(self):
        """ We may want to plot the results of tests that have multiple reads/writes """
        if self.steps > 1:
            self.result[plot_utils.PLOT_KEY] = []
            self.result[plot_utils.PLOT_KEY].append({
                'x': 'cutout_size', 'xlabel': 'Cutout volume',
                'y': 'read_time',
                'title': 'Cutout system test: {0}'.format(self.test_name)})
            self.result[plot_utils.PLOT_KEY].append({
                'x': 'cutout_size', 'xlabel': 'Cutout volume',
                'y': 'write_time',
                'title': 'Cutout system test: {0}'.format(self.test_name)})
            self.result[plot_utils.PLOT_KEY].append({
                'x': 'cutout_size', 'xlabel': 'Cutout volume',
                'y': 'match',
                'title': 'Cutout system test: {0}'.format(self.test_name)})
        super(SimpleBossCutoutTest, self).tearDown()

    def get_coordinates_list(self, params: dict):
        """ Use the axis ranges in params to calculate the extents of the cutout. Represent this as a tuple of
        (start, stop) tuples, like ((x0, x1), (y0, y1), (z0, z1), (time0, time1)). The time-axis tuple may be None if
        the test params do not contain 'time_range'. This function generates a list of these tuples-of-tuples, which
        enables it to 'schedule' a sequence of cutout reads or cutout writes.
        """
        unit_size = params['unit_size']
        step_size = params['step_size']
        x_sizes = [unit_size[0] + (j * step_size[0]) for j in range(0, self.steps)]
        y_sizes = [unit_size[1] + (j * step_size[1]) for j in range(0, self.steps)]
        z_sizes = [unit_size[2] + (j * step_size[2]) for j in range(0, self.steps)]
        t_sizes = [unit_size[3] + (j * step_size[3]) for j in range(0, self.steps)]
        # Round all block sizes up for cuboid alignment
        if self.cuboid_align:
            for i in range(0, self.steps):
                if x_sizes[i] % boss_test_utils.CACHE_SIZE_X is not 0:
                    x_sizes[i] += boss_test_utils.CACHE_SIZE_X - x_sizes[i] % boss_test_utils.CACHE_SIZE_X
                if y_sizes[i] % boss_test_utils.CACHE_SIZE_Y is not 0:
                    y_sizes[i] += boss_test_utils.CACHE_SIZE_Y - y_sizes[i] % boss_test_utils.CACHE_SIZE_Y
                if z_sizes[i] % boss_test_utils.CACHE_SIZE_Z is not 0:
                    z_sizes[i] += boss_test_utils.CACHE_SIZE_Z - z_sizes[i] % boss_test_utils.CACHE_SIZE_Z
        # todo: Determine "best" direction for moving the cutout? Defaults to x direction.
        # direction = 'x'
        x_starts = [0] * self.steps
        y_starts = [0] * self.steps
        z_starts = [0] * self.steps
        t_starts = [0] * self.steps
        for i in range(1, self.steps):
            x_starts[i] = x_sizes[i] + x_starts[i-1]
            # y, z, and t starts are zero
        # Return sets of (start, stop) pairs.
        x = [(x_starts[i], x_starts[i]+x_sizes[i]) for i in range(0, self.steps)]
        y = [(y_starts[i], y_starts[i]+y_sizes[i]) for i in range(0, self.steps)]
        z = [(z_starts[i], z_starts[i]+z_sizes[i]) for i in range(0, self.steps)]
        t = [(t_starts[i], t_starts[i]+t_sizes[i]) for i in range(0, self.steps)]
        return (x, y, z, t)

    def loop_cutout_behavior(self, x, y, z, t):
        self.result['cutout_size'] = []
        self.result['write_time'] = []
        self.result['read_time'] = []
        self.result['match'] = []
        remote = self.remote_resource
        channel = self.channel_resource
        for i in range(0, self.steps):
            x_size = x[i][1] - x[i][0]
            y_size = y[i][1] - y[i][0]
            z_size = z[i][1] - z[i][0]
            t_size = t[i][1] - t[i][0]
            self.result['cutout_size'].append(x_size * y_size * z_size * t_size)
            # phase 1: write
            write_data = numpy_utils.cuboid(x_size, y_size, z_size, t_size)
            print('Cutout coords: x={0}, y={1}, z={2}, t={3}'.format(x[i], y[i], z[i], t[i]))
            # if self.cache_hit:
            #     remote.create_cutout(channel, self.resolution, x[i], y[i], z[i], write_data, t[i])
            #     if self.delay > 0:
            #         time.sleep(self.delay)
            tick = time.time()
            remote.create_cutout(channel, self.resolution, x[i], y[i], z[i], write_data, t[i])
            self.result['write_time'].append(time.time() - tick)
            if self.delay > 0:
                time.sleep(self.delay)
            # phase 2: read
            if self.cache_hit:
                remote.get_cutout(channel, self.resolution, x[i], y[i], z[i], t[i])
                if self.delay > 0:
                    time.sleep(self.delay)
            tick = time.time()
            read_data = remote.get_cutout(channel, self.resolution, x[i], y[i], z[i], t[i])
            self.result['read_time'].append(time.time() - tick)
            # phase 3: verify
            match_percent = numpy_utils.array_match_percentage(write_data, read_data)
            self.result['match'].append(match_percent)
        return 1

    @systemtest.systemtestmethod
    def one_cutout_test(self, params=None):
        """ System test case: Single upload and download of a data cuboid.
        Record the duration for write operation and the read operation.
        """
        if params is None:
            params = self.parameters
            params['steps'] = 1
        params = self.validate_params(params)
        x, y, z, t = self.get_coordinates_list(params)
        self.loop_cutout_behavior(x, y, z, t)
        return

    @systemtest.systemtestmethod
    @unittest.expectedFailure
    def invalid_cutout_test(self, params=None):
        """ System test case: Badly configured cutouts.
        """
        if params is None:
            params = self.parameters
        # Extra optional parameter: Expected error status code.
        expected_status = int(params['status']) if 'status' in params else 200
        params = self.validate_params(params)
        params['status'] = expected_status
        x, y, z, t = self.get_coordinates_list(params)
        try:
            self.loop_cutout_behavior(x, y, z, t)
        except requests.exceptions.HTTPError as e:
            self.assertEqual(expected_status, e.response.status_code)
        return

    @systemtest.systemtestmethod
    def multiple_cutout_test(self, params=None):
        """ System test case: Single upload of a data cuboid. Record the duration for write operation to complete.
        """
        if params is None:
            params = self.parameters
        params = self.validate_params(params)
        x, y, z, t = self.get_coordinates_list(params)
        self.loop_cutout_behavior(x, y, z, t)
        return
