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


def write(data: dict, filename: str=None):
    """Write and save the contents of a python dictionary into a JSON file.
    Args:
        data (dict): The python dict with the data.
        filename (str): The name of the output JSON file where to save the data.
    """
    assert bool(data), "Empty dictionary"
    data = OrderedDict(data)
    # print('Writing = {0}'.format(data))
    data_formatted = json.dumps(data, ensure_ascii=False, indent=4)
    if filename is None:
        print(data_formatted)
    else:
        f = open(filename, 'w')
        f.write(data_formatted)
        f.close()
