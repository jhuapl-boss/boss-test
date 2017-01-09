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


class SimpleBossImageTest(simple_boss_test.SimpleBossTest):
    """ System tests for the Boss image service API, testing different write/read patterns.
    Intended as a simplified version of sys_test_boss_image.BossImageSystemTest.
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

    def validate_params(self, test_params: dict, is_constant_range=True):
        """ Validate the test input parameters """
        # Defaults
        self.orientation = 'xy'
        if 'orientation' in test_params:
            self.assertIn(test_params['orientation'].lower(), ['xy', 'yz', 'xz'])
            self.orientation = test_params['orientation'].lower()
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
            'orientation': self.orientation,
            'delay': self.delay
        }

    def tearDown(self):
        """ We may want to plot the results of tests that have multiple reads/writes """
        self.result[plot_utils.PLOT_KEY] = []
        self.result[plot_utils.PLOT_KEY].append({
            'x': 'image_size', 'xlabel': 'Image volume',
            'y': 'read_time',
            'title': 'Image system test: {0}'.format(self.test_name)})
        super(SimpleBossImageTest, self).tearDown()

    def get_coordinates_list(self, params: dict):
        """ Use the axis ranges in params to calculate the extents of the image. Represent this as a tuple of
        (start, stop) tuples, like ((x0, x1), (y0, y1), (z0, z1), (time0, time1)). The time-axis tuple may be None if
        the test params do not contain 'time_range'. This function generates a list of these tuples-of-tuples, which
        enables it to 'schedule' a sequence of image reads or image writes.
        """
        unit_size = params['unit_size']
        step_size = params['step_size']
        x_sizes = [unit_size[0] + (j * step_size[0]) for j in range(0, self.steps)]
        y_sizes = [unit_size[1] + (j * step_size[1]) for j in range(0, self.steps)]
        z_sizes = [unit_size[2] + (j * step_size[2]) for j in range(0, self.steps)]
        # t_sizes = [unit_size[3] + (j * step_size[3]) for j in range(0, self.steps)]
        # Round all block sizes up for cuboid alignment
        if self.cuboid_align:
            for i in range(0, self.steps):
                if x_sizes[i] % boss_test_utils.CACHE_SIZE_X is not 0:
                    x_sizes[i] += boss_test_utils.CACHE_SIZE_X - x_sizes[i] % boss_test_utils.CACHE_SIZE_X
                if y_sizes[i] % boss_test_utils.CACHE_SIZE_Y is not 0:
                    y_sizes[i] += boss_test_utils.CACHE_SIZE_Y - y_sizes[i] % boss_test_utils.CACHE_SIZE_Y
                if z_sizes[i] % boss_test_utils.CACHE_SIZE_Z is not 0:
                    z_sizes[i] += boss_test_utils.CACHE_SIZE_Z - z_sizes[i] % boss_test_utils.CACHE_SIZE_Z
        # todo: Determine "best" direction for moving the image. Default is x axis.
        # direction = 'x'
        x_starts = [0] * self.steps
        y_starts = [0] * self.steps
        z_starts = [0] * self.steps
        # t_starts = [0] * self.steps
        for i in range(1, self.steps):
            x_starts[i] = x_sizes[i] + x_starts[i-1]
            # y, z, and t starts are zero
        # Return sets of (start, stop) pairs.
        if 'x' in self.orientation:
            x = [(x_starts[i], x_starts[i]+x_sizes[i]) for i in range(0, self.steps)]
        else:
            x = [i * step_size[0] for i in range(0, self.steps)]
        if 'y' in self.orientation:
            y = [(y_starts[i], y_starts[i]+y_sizes[i]) for i in range(0, self.steps)]
        else:
            y = [i * step_size[1] for i in range(0, self.steps)]
        if 'z' in self.orientation:
            z = [(z_starts[i], z_starts[i]+z_sizes[i]) for i in range(0, self.steps)]
        else:
            z = [i * step_size[2] for i in range(0, self.steps)]
        # t = [(t_starts[i], t_starts[i]+t_sizes[i]) for i in range(0, self.steps)]
        t = [i * step_size[3] for i in range(0, self.steps)]
        return (x, y, z, t)

    def loop_image_behavior(self, x, y, z, t):
        self.result['image_size'] = []
        self.result['read_time'] = []
        accept = 'image/png'
        remote = self.remote_resource
        channel = self.channel_resource
        for i in range(0, self.steps):
            x_size = 1 if 'x' not in self.orientation else x[i][1] - x[i][0]
            y_size = 1 if 'y' not in self.orientation else y[i][1] - y[i][0]
            z_size = 1 if 'z' not in self.orientation else z[i][1] - z[i][0]
            x_str = str(x[i]) if 'x' not in self.orientation else '{0}:{1}'.format(x[i][0], x[i][1])
            y_str = str(y[i]) if 'y' not in self.orientation else '{0}:{1}'.format(x[i][0], x[i][1])
            z_str = str(z[i]) if 'z' not in self.orientation else '{0}:{1}'.format(x[i][0], x[i][1])
            t_str = str(t[i])
            # t_size = t[i]
            self.result['image_size'].append(x_size * y_size * z_size)
            # form the URL
            self.result['url'] = "https://{0}/v{1}/image/{2}".format(
                boss_test_utils.get_host(remote),
                boss_test_utils.DEFAULT_VERSION,
                "/".join([
                    self.collection_resource.name,
                    self.experiment_resource.name,
                    channel.name,
                    self.orientation,
                    str(self.resolution), x_str, y_str, z_str, t_str]))
            # Force cache hit by reading twice
            print('Image coords: x={0}, y={1}, z={2}, t={3}'.format(x[i], y[i], z[i], t[i]))
            if self.cache_hit:
                boss_test_utils.get_obj(remote, self.result['url'], accept)
                if self.delay > 0:
                    time.sleep(self.delay)
            tick = time.time()
            obj = boss_test_utils.get_obj(remote, self.result['url'], accept)
            self.result['read_time'].append(time.time() - tick)
            self.result['status_code'] = obj.status_code
        return 1

    @systemtest.systemtestmethod
    def one_image_test(self, params=None):
        """ System test case: Single download of an image. Record the duration of the GET request.
        """
        if params is None:
            params = self.parameters
            params['steps'] = 1
        params = self.validate_params(params)
        x, y, z, t = self.get_coordinates_list(params)
        self.loop_image_behavior(x, y, z, t)
        return

    @systemtest.systemtestmethod
    @unittest.expectedFailure
    def invalid_image_test(self, params=None):
        """ System test case: Badly configured images.
        """
        if params is None:
            params = self.parameters
        # Extra optional parameter: Expected error status code.
        expected_status = int(params['status']) if 'status' in params else 200
        params = self.validate_params(params)
        params['status'] = expected_status
        x, y, z, t = self.get_coordinates_list(params)
        try:
            self.loop_image_behavior(x, y, z, t)
        except requests.exceptions.HTTPError as e:
            self.assertEqual(expected_status, e.response.status_code)
        return

    @systemtest.systemtestmethod
    def multiple_image_test(self, params=None):
        """ System test case: Download multiple images. Record the duration of each GET request.
        """
        if params is None:
            params = self.parameters
        params = self.validate_params(params)
        x, y, z, t = self.get_coordinates_list(params)
        self.loop_image_behavior(x, y, z, t)
        return
