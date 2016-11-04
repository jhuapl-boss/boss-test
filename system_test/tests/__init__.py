# Try to import the classes from the python files in this directory
if __name__ == 'tests':
    import os, re
    filenames_list = os.listdir(os.path.dirname(__file__))
    for filename in filenames_list:
        if not re.match("__init__\.py",filename) and re.match(".+\.py",filename):
            cmd = "from .{0} import *".format(filename[:-3])
            # print(cmd)
            exec(cmd)
