#!/usr/bin/env python3
import json, re, time, math
from collections import OrderedDict

def readNdioCutoutTest(filename: str) -> OrderedDict:
    from jsmin import jsmin # allows comments
    with open(filename) as file_data:
        json_text = jsmin(file_data.read())
    json_dict = json.loads(json_text, object_pairs_hook=OrderedDict)
    return json_dict

def convert_to_text(file_json:str):
    indent = "  "
    digits = 6
    file_out = file_json.replace(".json",".txt")
    data = readNdioCutoutTest(file_json)
    # Write the start timestamp at the top of the file #
    f = open(file_out, 'w')
    f.seek(0)

    def write(line: str, newline=True):
        print(line)
        f.write("{0}".format(line))
        if newline:
            f.write("\n")
    write ("Note: {0}\n".format(data['note']))
    write( "Collection: name=\"{0}\"".format(data['collection']['name']) )
    write( "Coordinate frame: name=\"{0}\", dimensions=x:[{1}, {2}], y:[{3}, {4}], z: [{5}, {6}], units=\"{7}\"".format(
        data['coordinate_frame']['name'],
        data['coordinate_frame']['x_start'],
        data['coordinate_frame']['x_stop'],
        data['coordinate_frame']['y_start'],
        data['coordinate_frame']['y_stop'],
        data['coordinate_frame']['z_start'],
        data['coordinate_frame']['z_stop'],
        data['coordinate_frame']['voxel_unit'] ))
    write ("Experiment: name=\"{0}\", max time sample={1}".format(
        data['experiment']['name'], data['experiment']['max_time_sample']))
    write ("Default channel: name=\"{0}\", datatype=\"{1}\"".format(data['channel']['name'], data['channel']['datatype']))
    write ("Layer: name=\"{0}\", datatype=\"{1}\"".format(data['layer']['name'], data['layer']['datatype']))
    write ("")

    test_count = 0
    for key in data:
        match = re.match(".+\_test", key)
        if match:
            out = data[key]
            for i in range(len(out)):
                test_count += 1
                write("Test #{3}: {0} (#{1}/{2})".format(key, i+1, len(out), test_count))
                write("{0}Description: \"{1}\"".format(indent, out[i]['description']))
                write("{0}Start time: {1}".format(indent, time.asctime(time.gmtime(out[i]['start_time'])) ))
                line = "{0}Data range: x={1}, y={2}, z={3}, t={4}".format(indent,
                    out[i]['args']['x_range'],
                    out[i]['args']['y_range'],
                    out[i]['args']['z_range'],
                    "None" if "time_range" not in out[i]['args'] else out[i]['args']['time_range'])
                iterations = 1
                if len(out[i]['args']['x_range'])>2:
                    iterations = (out[i]['args']['x_range'][1]-out[i]['args']['x_range'][0])/out[i]['args']['x_range'][2]
                elif len(out[i]['args']['y_range'])>2:
                    iterations = (out[i]['args']['y_range'][1]-out[i]['args']['y_range'][0])/out[i]['args']['y_range'][2]
                elif len(out[i]['args']['z_range'])>2:
                    iterations = (out[i]['args']['z_range'][1]-out[i]['args']['z_range'][0])/out[i]['args']['z_range'][2]
                elif 'time_range' in out[i]['args'] and len(out[i]['args']['time_range'])>2:
                    iterations = (out[i]['args']['time_range'][1]-out[i]['args']['time_range'][0])/out[i]['args']['time_range'][2]
                if iterations > 1:
                    line = "{0}, iterations={1}".format(line, int(iterations))
                write(line)
                if "channel" not in out[i]['args']:
                    write("{0}Using default channel".format(indent))
                else:
                    write("{0}Using new channel: datatype=\"{1}\"".format(indent, out[i]['args']['channel']['datatype']))
                if isinstance(out[i]['duration'],list):
                    if len(out[i]['duration']) == 0:
                        write("{0}Times: []".format(indent))
                    else:
                        dur_min = round(min(out[i]['duration']), ndigits=digits)
                        dur_max = round(max(out[i]['duration']), ndigits=digits)
                        dur_avg = round(sum(out[i]['duration'])/len(out[i]['duration']), ndigits=digits)
                        variance = map(lambda x: x*x-dur_avg*dur_avg, out[i]['duration'])
                        stddev = round( math.sqrt(sum(variance)/len(out[i]['duration'])), ndigits=digits)
                        # write("{0}Times: {1}".format(indent,
                        #      list(map(lambda x: round(x, ndigits=digits), out[i]['duration']))))
                        write("{0}Times: count={1}, min={2} s, max={3} s, mean={4} s, std dev={5} s".format(indent,
                            len(out[i]['duration']), dur_min, dur_max, dur_avg, stddev))
                    # for j in range(len(out[i]['duration'])):
                    #     dur = round(out[i]['duration'][j], 4)
                    #     # dur = out[i]['duration'][j]
                    #     if j==len(out[i]['duration'])-1:
                    #         write("{0}".format(dur))
                    #     else:
                    #         write("{0}, ".format(dur),newline=False)
                elif isinstance(out[i]['duration'],float):
                    write("{0}Time: {1}s".format(indent, round(out[i]['duration'], ndigits=digits)))
                else:
                    write("[]")
                write("{0}Error: \"{1}\"".format(indent, out[i]['error']))
                write("")
    f.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Parser that accepts configuration file name')
    parser.add_argument('json', metavar="<file>", nargs='*', help='JSON configuration file name')
    args = parser.parse_args()
    if (args):
        filename = args.json[0]
        print(filename)
        convert_to_text(filename)
    else:
        print('No data')