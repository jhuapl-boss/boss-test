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
import argparse, sys, time, unittest
from os import path
from requests import HTTPError
from collections import OrderedDict
from utils import json_utils, boss_test_utils

# AUTO_PLOT = True
AUTO_PLOT = False
WRITE_FILES = True or False


class SystemTest(unittest.TestCase):
    """ Base class for System Tests """

    # Static class attributes
    _class_config = None             # From the JSON configuration for this class
    _parser_args = None              # Values from the initial command line arguments (from argparse.parse_args)
    _class_results = OrderedDict()   # Static list of test outputs of all tests in this class
    _output_file = None             # Where to write the test outputs

    # Object attributes
    __test_name = None              # Name of the method for this specific test
    __test_parameters = None        # Parameters given to this specific test
    result = None                   # Result of this specific test

    def __init__(self, method_name, method_parameters):
        super(SystemTest, self).__init__(method_name)
        self.__test_name = method_name
        self.__test_parameters = method_parameters
        self.result = OrderedDict()

    @property
    def class_config(self):
        """ Returns the static configuration of this class, as specified in the JSON configuration file. """
        return type(self)._class_config

    @property
    def class_results(self):
        """ Returns the static list of results for tests in this class. """
        return type(self)._class_results[type(self).__name__]

    @property
    def parameters(self):
        """ Returns the parameters for this instance of the test. """
        return self.__test_parameters

    @property
    def parser_args(self):
        """ Returns the parsed command line arguments. """
        return type(self)._parser_args

    @property
    def test_name(self):
        """ Returns the test method name for this instance of the test. """
        return self.__test_name

    def add_result(self, result_value=None):
        """Single test object instance - Store test result """
        if self.test_name not in type(self)._class_results[type(self).__name__]:
            type(self)._class_results[type(self).__name__][self.test_name] = list([])
        output_value = {
            'params': self.parameters,
            'result': result_value if bool(result_value) else self.result
        }
        type(self)._class_results[type(self).__name__][self.test_name].append(output_value)

    # The methods below should only be called in child class methods that would override them.
    def tearDown(self):
        self.add_result(self.result)

# This file should be run from the command line: python systemtest.py <args>
if __name__ == '__main__':
    # import re
    from tests import *
    __unittest = True

    # Parse the command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file',
                        metavar='N',
                        help='Required: JSON configuration file name')
    parser.add_argument('--output', '-o',
                        default='output',
                        help='Optional: Output directory')
    # parser.add_argument('--quiet', '-q',
    #                     action='store_true',
    #                     help='Optional: Suppress print output')
    parser.add_argument('--version', '-v',
                        default=boss_test_utils.DEFAULT_VERSION,
                        help='Optional: Boss API version')
    parser.add_argument('--domain', '-d',
                        # default=boss_test_utils.DEFAULT_DOMAIN,
                        help='Optional: Domain name')
    parser_args = parser.parse_args()
    if not bool(parser_args.input_file):
        parser.print_usage()
        raise Exception('Missing argument: configuration file name')

    # Parse the JSON configuration file into a python dictionary
    json_config = json_utils.read(parser_args.input_file)
    start_time = time.gmtime()
    output_dir = '{0}/{1}/{2}_{3:0>2}_{4:0>2}_{5:0>2}_{6:0>2}_{7:0>2}'.format(
        # Optional command argument: output directory #
        path.dirname(path.realpath(__file__)),
        'output' if not bool(parser_args.output) else parser_args.output,
        start_time.tm_year,
        start_time.tm_mon,
        start_time.tm_mday,
        start_time.tm_hour,
        start_time.tm_min,
        start_time.tm_sec)

    # Parse the JSON configuration file and define the system tests to perform
    # ToDo: This is disorganized and/or difficult to read
    suite = unittest.TestSuite()
    scheduled_classes = list([])
    for json_class_name in json_config:
        if hasattr(sys.modules[__name__], json_class_name):
            cls = getattr(sys.modules[__name__], json_class_name)
            scheduled_classes.append(cls)

    for cls in scheduled_classes:
        cls._class_config = json_config[cls.__name__]
        cls._output_file = '{0}/{1}.json'.format(output_dir, cls.__name__)
        cls._parser_args = parser_args
        cls._class_results[cls.__name__] = OrderedDict()
        valid_method_names = [func for func in dir(cls) if callable(getattr(cls, func))]
        # Loop through the non-methods to add static variables
        for keyname in cls._class_config:
            if keyname not in valid_method_names:
                cls._class_results[cls.__name__][keyname] = json_config[cls.__name__][keyname]
        # Loop through the methods to schedule tests
        for keyname in cls._class_config:
            if keyname in valid_method_names:
                cls._class_results[cls.__name__][keyname] = list([])
                parameters = cls._class_config[keyname]
                if not isinstance(parameters, list):
                    parameters = [parameters]
                for param in parameters:
                    suite.addTest(cls(keyname, param))
                    print('added test: {0}.{1}'.format(cls.__name__, keyname, param))

    print('Start time: {0}'.format(time.asctime(start_time)))

    results = unittest.TextTestRunner().run(suite)

    if WRITE_FILES and len(scheduled_classes) > 0:
        print('Output directory: {0}'.format(output_dir))
        if not os.path.isdir(parser_args.output):
            os.mkdir(parser_args.output)
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        # Write:
        for cls in scheduled_classes:
            if bool(cls._class_results[cls.__name__]) and bool(cls._output_file):
                json_utils.write(cls._class_results[cls.__name__], cls._output_file)
                print('\n{0}: Results saved to {1}'.format(cls.__name__, cls._output_file))
            else:
                print('\n{0}: Results not saved!'.format(cls.__name__))

        if AUTO_PLOT:
            from utils import plot_utils
            plot_utils.read_directory(output_dir)


# Custom decorator that designates a method as a system test method
# Currently does not do anything but we can add features later
def systemtestmethod(test_method):
    """Decorator for system test functions. Captures errors and inserts them into the output."""
    def wrapper(*args, **kwargs):
        test_self = args[0]
        try:
            test_method(*args, **kwargs)
        except HTTPError as e:
            test_self.result['error'] = str(e)
            test_self.result['status'] = str(e.response.status_code)
            # print(e.request)
            # print(e.strerror)
            raise e
        except Exception as e:
            test_self.result['error'] = str(e)
            raise e
    return wrapper

