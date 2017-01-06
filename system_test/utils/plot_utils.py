#!/usr/bin/env python3
# Copyright 2016 The Johns Hopkins University Applied Physics Laboratory
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import numpy
import os
import re
if __name__ == '__main__':
    import argparse
    import json_utils
else:
    from utils import json_utils
import matplotlib.pyplot as pyplot

PLOT_KEY = '_PLOT_'

# Todo: Allow y-axis to be list of names, so that multiple arrays can be plotted simultaneously.

# Display a plot of two arrays #
def show_plot(xarray, yarray, xlabel: str='x', ylabel: str='y', title: str=""):
    """Whenever an axis pair is detected, creates a line plot using those axes. This function is called by read_json()
    and is not designed to be called directly.
    Args:
        xarray (list/numpy.ndarray) : Values for the x-axis
        yarray (list/numpy.ndarray) : Values for the y-axis
        xlabel (str) : Label for the x-axis
        ylabel (str) : Label for the y-axis
        title (str) : Title for the line plot
    """
    for i in range(0, len(xarray)):
        if not isinstance(xarray[i], (int, float)):
            # warnings.showwarning('Some x-Axis values are not numeric',Warning,filename,0)
            break
        elif not isinstance(yarray[i], (int, float)):
            # warnings.showwarning('Some y-Axis values are not numeric',Warning,filename,0)
            break
    try:
        x_lims = [min(x for x in xarray if x is not None), max(x for x in xarray if x is not None)]
        y_lims = [min(y for y in yarray if y is not None), max(y for y in yarray if y is not None)]
        # If data is constant value, adjust axes limits #
        x_lims[1] = (x_lims[1] if x_lims[0] == x_lims[1] else x_lims[1]+1)
        y_lims[1] = (y_lims[1] if y_lims[0] == y_lims[1] else y_lims[1]+1)
        # f = pyplot.gcf()
        # ax = f.add_axes([x_lims[0], y_lims[0], x_lims[1], y_lims[1]])
        pyplot.plot(xarray, yarray)
        pyplot.draw()
        # axes = pyplot.gca()
        # axes.set_xlim([x_lims[0]-x_margin, x_lims[1]+x_margin])
        # axes.set_ylim([y_lims[0]-y_margin, y_lims[1]+y_margin])
        pyplot.grid(True)
        pyplot.xlabel(xlabel)
        pyplot.ylabel(ylabel)
        if not bool(title):
            title = 'Plot {0} vs {1}'.format(ylabel, xlabel)
        pyplot.title(title)
    except Exception as e:
        # print('ERROR: {0}'.format(str(e)))
        raise e
    return


def read_json(data: dict, keyword: str):
    """Parse a JSON dictionary and find array pairs to plot. Array pairs are identified when the output has a key
    called show_plot (which may be set as json_plot.PLOY_KEY). The value of this dictionary entry should be a 2-element
    vector, where both elements are strings that are key names. These keys should refer to values in the dictionary
    that are numeric lists. For example, the unit test function result (in the JSON) could be written as:
    {
        'x_vals':[1, 2, 3, 4],
        'y_vals':[10,11,12,13,
        <PLOT_KEY>:{'x_vals', 'y_vals'},
        ...
    }
    Args:
        data (dict) : Result of load()
        keyword (str) : The key of the dictionary where we are looking. This is because the function is recursive and
                        may operate on nested dictionaries.
    """
    plot_list = []
    if isinstance(data, dict):
        for key in data:
            if key == keyword:
                plots_info = data[key] if isinstance(data[key], list) else list([data[key]])
                for info in plots_info:
                    try:
                        y_key = info['y']
                        y_vals = data[y_key]
                        x_key = info['x']
                        x_vals = data[x_key]
                        assert bool(x_vals), 'Empty x axis data'
                        assert bool(y_vals), 'Empty y axis data'
                        title = info['title'] if 'title' in info else ""
                        xlabel = info['xlabel'] if 'xlabel' in info else x_key
                        ylabel = info['ylabel'] if 'ylabel' in info else y_key
                        # if 'x' not in info or min(x_vals)==max(x_vals):
                        #     if min(x_vals)==max(x_vals):
                        #         title += ' ({0}={1})'.format(x_key, max(x_vals))
                        #     x_vals = list(range(1,len(y_vals)+1))
                        #     xlabel = 'iterations ({0})'.format(len(x_vals))
                        plot_list.append({'x': x_vals,
                                          'y': y_vals,
                                          'xlabel': xlabel,
                                          'ylabel': ylabel,
                                          'title': title})
                    except Exception as e:
                        # print(e)
                        raise e
                        pass
            else:
                p = read_json(data[key], keyword)
                if p:
                    plot_list += p
    elif isinstance(data, (list, numpy.ndarray)):
        for item in data:
            p = read_json(item, keyword)
            if p:
                plot_list += p
    return plot_list


def read_files(file_names):
    """Scan a file or list of files for plot data, and then display plots."""
    if not isinstance(file_names, list):
        file_names = list([file_names])
    plots = list([])
    for i in range(0, len(file_names)):
        try:
            json_data = json_utils.read(file_names[0])
            if json_data:
                plots_recursive = read_json(json_data, PLOT_KEY)
                for j in range(0, len(plots_recursive)):
                    plots_recursive[j]['filename'] = file_names[i]
                plots += plots_recursive
        except Exception as e:
            print('Exception while reading {0}: {1}'.format(file_names[i], str(e)))
    for k in range(0, len(plots)):
        # pyplot.figure()
        show_plot(plots[k]['x'],
                  plots[k]['y'],
                  plots[k]['xlabel'],
                  plots[k]['ylabel'],
                  plots[k]['title'],)
        pyplot.show()
        # print(plots[k])
        # imgfile = '{0}.png'.format(
        #     # plots[k]['filename'].replace('.json', ''),
        #     re.sub(r':|;|\*| |!|\$|,', '_', plots[k]['title']))
        # print(imgfile)
        # pyplot.savefig(imgfile)


def read_directory(dir_name):
    """Scan a directory for files with plot data. Make sure to use each file's full name."""
    file_list = [('{0}/{1}'.format(dir_name, x) if dir_name not in x else x) for x in os.listdir(dir_name)]
    read_files(file_list)
    # for filename in os.listdir(dirname):
    #     print('Trying to read {0}...'.format(filename))
    #     read_file('/'.join([dirname, filename]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parser that accepts configuration file name')
    parser.add_argument('files', metavar='N',
                        nargs='+',
                        help='JSON output file(s) with numeric array data')
    args = parser.parse_args()
    read_files(args.files)
