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

import json
from collections import OrderedDict


def read(filename: str) -> OrderedDict:
    """Parse a JSON file into a python dictionary. Uses jsmin so that file contents may contain javascript-style
     comments, which are ignored.
    Args:
        filename (str) : The name of a JSON file.
    Returns:
        OrderedDict : Dictionary structure that mimics the JSON hierarchy.
    """
    from jsmin import jsmin # allows comments
    with open(filename) as file_data:
        json_text = jsmin(file_data.read())
    json_dict = json.loads(json_text, object_pairs_hook=OrderedDict)
    return json_dict


def write(data:dict, filename:str=None):
    """Write and save the contents of a python dictionary into a JSON file.
    Args:
        data (dict): The python dict with the data.
        filename (str): The name of the output JSON file where to save the data.
    """
    assert bool(data), "Empty dictionary"
    data_formatted = json.dumps(OrderedDict(data), ensure_ascii=False, indent=4)
    if filename is None:
        print(data_formatted)
    else:
        f = open(filename, 'w')
        f.write(data_formatted)
        f.close()

# d = 'output/16_09_30_22_44_33/'
# file_in = '{0}BossCutoutTest.json'.format(d)
# file_out = '{0}BossCutoutTest-C4.json'.format(d)
# json_data = read(file_in)
# D = {
#     'write_cache_miss_throughput_test':'Write cache miss',
#     'read_cache_miss_throughput_test':'Read cache miss',
#     'write_partial_miss_throughput_test':'Write partial cache miss',
#     'read_partial_miss_throughput_test':'Read partial cache miss'
# }
# for testname in json_data:
#     if isinstance(json_data[testname],list):
#         for i in range(0,len(json_data[testname])):
#
#             if ('duration' in json_data[testname][i]) and isinstance(json_data[testname][i]['duration'],list):
#                 args = json_data[testname][i]['args']
#                 if 'channel' in args:
#                     chan = 'New {0} channel'.format(args['channel']['datatype'])
#                 else:
#                     chan = 'Reused {0} channel'.format(json_data['channel']['datatype'])
#                 if len(args['x_range'])==3:
#                     x = 'x=[{0}:{1}:{2}]'.format(args['x_range'][0], args['x_range'][2], args['x_range'][1])
#                 else:
#                     x = 'x=[{0}:{1}]'.format(args['x_range'][0], args['x_range'][1])
#                 if len(args['y_range'])==3:
#                     y = ', y=[{0}:{1}:{2}]'.format(args['y_range'][0], args['y_range'][2], args['y_range'][1])
#                 else:
#                     y = ', y=[{0}:{1}]'.format(args['y_range'][0], args['y_range'][1])
#                 if len(args['z_range'])==3:
#                     z = ', z=[{0}:{1}:{2}]'.format(args['z_range'][0], args['z_range'][2], args['z_range'][1])
#                 else:
#                     z = ', z=[{0}:{1}]'.format(args['z_range'][0], args['z_range'][1])
#                 if 'time_range' not in args:
#                     t = ''
#                 elif len(args['time_range']) == 3:
#                     t = ', t=[{0}:{1}:{2}]'.format(args['time_range'][0], args['time_range'][2], args['time_range'][1])
#                 else:
#                     t = ', t=[{0}:{1}]'.format(args['time_range'][0], args['time_range'][1])
#                 title = '{0}, {1}, \n{2}{3}{4}{5}'.format(D[testname], chan, x, y, z, t)
#                 p = {
#                     'x':'size', 'y':'duration', 'xlabel':'data size', 'ylabel':'operation time','title':title
#                 }
#                 json_data[testname][i].pop('PLOT_AXES',None)
#                 json_data[testname][i]['_PLOT_'] = p
# write(json_data, file_out)