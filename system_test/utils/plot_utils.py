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

PLOT_KEY = "_PLOT_"


if __name__ == '__main__':
    import json_utils
    import warnings
    import matplotlib.pyplot as pyplot
    from collections import OrderedDict
else:
    from utils import json_utils


# Display a plot of two arrays #
def plot_axes(xarray:list, yarray:list, xlabel:str="x", ylabel:str="y", title:str="", index:int=0):
    """Whenever an axis pair is detected, creates a line plot using those axes. This function is called by get_plots()
    and is not designed to be called directly.
    Args:
        xarray (list) : Values for the x-axis
        yarray (list) : Values for the y-axis
        xlabel (str) : Label for the x-axis
        ylabel (str) : Label for the y-axis
        title (str) : Title for the line plot
    """
    assert(len(xarray)==len(yarray)), "Axis size mismatch, {0} x, {1} y".format(len(xarray), len(yarray))
    for i in range(0,len(xarray)):
        if not isinstance(xarray[i],(int, float)):
            # warnings.showwarning("Some x-Axis values are not numeric",Warning,filename,0)
            break
        elif not isinstance(yarray[i],(int, float)):
            # warnings.showwarning("Some y-Axis values are not numeric",Warning,filename,0)
            break
    try:
        x_lims = [min(x for x in xarray if x is not None), max(x for x in xarray if x is not None)]
        y_lims = [min(y for y in yarray if y is not None), max(y for y in yarray if y is not None)]
        # If data is constant value, adjust axes limits #
        x_lims[1] = (x_lims[1] if x_lims[0]==x_lims[1] else x_lims[1]+1)
        y_lims[1] = (y_lims[1] if y_lims[0]==y_lims[1] else y_lims[1]+1)
        f = pyplot.gcf()
        # ax = f.add_axes([x_lims[0], y_lims[0], x_lims[1], y_lims[1]])
        pyplot.plot(xarray,yarray)
        pyplot.draw()
        # axes = pyplot.gca()
        # axes.set_xlim([x_lims[0]-x_margin, x_lims[1]+x_margin])
        # axes.set_ylim([y_lims[0]-y_margin, y_lims[1]+y_margin])
        pyplot.grid(True)
        pyplot.xlabel(xlabel)
        pyplot.ylabel(ylabel)
        if not bool(title):
            title = "Plot {0}: {1} vs. {2}".format(index, ylabel, xlabel)
        pyplot.title(title)
    except Exception as e:
        print("ERROR: {0}".format(str(e)))
    return


def get_plots(data:dict, keyword:str):
    """Parse a JSON dictionary and find array pairs to plot. Array pairs are identified when the output has a key
    called PLOT_AXES (which may be set as json_plot.PLOY_KEY). The value of this dictionary entry should be a 2-element
    vector, where both elements are strings that are key names. These keys should refer to values in the dictionary
    that are numeric lists. For example, the unit test function result (in the JSON) could be written as:
    {
        'x_vals':[1, 2, 3, 4],
        'y_vals':[10,11,12,13,
        'PLOT_KEY':{'x_vals', 'y_vals'},
        ...
    }
    Args:
        data (dict) : Result of load()
        keyword (str) : The key of the dictionary where we are looking. This is because the function is recursive and
                        may operate on nested dictionaries.
    """
    plots = []
    if isinstance(data,dict):
        for key in data:
            if key==keyword:
                plots_info = data[key] if isinstance(data[key],list) else list([data[key]])
                for info in plots_info:
                    try:
                        y_key = info['y']
                        y_vals = data[y_key]
                        x_key = info['x']
                        x_vals = data[x_key]
                        assert(x_vals), "Empty x axis data"
                        assert(y_vals), "Empty y axis data"
                        title = info['title'] if 'title' in info else ""
                        xlabel = info['xlabel'] if 'xlabel' in info else x_key
                        ylabel = info['ylabel'] if 'ylabel' in info else y_key
                        # if 'x' not in info or min(x_vals)==max(x_vals):
                        #     if min(x_vals)==max(x_vals):
                        #         title += " ({0}={1})".format(x_key, max(x_vals))
                        #     x_vals = list(range(1,len(y_vals)+1))
                        #     xlabel = "iterations ({0})".format(len(x_vals))
                        plots.append({
                            "x":x_vals, "y":y_vals, "xlabel":xlabel, "ylabel":ylabel, "title":title
                        })
                    except:
                        pass
            else:
                p = get_plots(data[key],keyword)
                if p:
                    plots += p
    elif isinstance(data,list):
        for item in data:
            p = get_plots(item,keyword)
            if p:
                plots += p
    return plots


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Parser that accepts configuration file name')
    parser.add_argument('--json-file','-f',
                        metavar="<file>",
                        nargs='+',
                        help='Name of JSON file that contains axes data')
    args = parser.parse_args()
    for infile in args.json_file:
        jsondata = json_utils.read(infile)
        if jsondata:
            plots = get_plots(jsondata, PLOT_KEY)
            idx = 1
            for plotinfo in plots:
                pyplot.figure(idx)
                plot_axes(plotinfo["x"], plotinfo["y"], plotinfo["xlabel"], plotinfo["ylabel"], plotinfo["title"], idx)
                idx += 1
            pyplot.show()
        else:
            print('No data')
