# System Test Directory

#### systemtest.py
Contains the base SystemTest class and command line handling.

## Setup
1. Install python (3.5+) on your system
2. Use git to clone the boss-test repository
3. Install the requirements (`pip install -r requirements.txt`)

## Usage
`python systemtest.py <arguments>`

#### Required arguments:
* Name of the configuration JSON file

#### Optional arguments:
* --output, -o    = Name of the root of the output directory, where the output JSON file is written

Example:
> cd boss-test/system_test

> python3 systemtest.py -i input/mytestconfig.json

---
## Directory structure

#### input/
Location of configuration JSON files.  Each file contains the JSON input for one or more of the classes,
defining which test functions to run and what parameters to use for each function.

To use a system test child class, the JSON must contain an object with the name of that class. The value of this field
must be a dictionary.  If the name of an entry is the name of a test function, then the values of that field are
used as parameters (see paragraph below). Otherwise, if the name of an entry is not an existing function in the class,
then it will be stored as a static variable.

You can configure multiple classes if you list multiple class names in the same input file.
You may also insert javascript-style comments in your JSON file.

To run a test function in your child class, the JSON must contain a field with the name of that
function. The value of that field must be an array, where each entry in the array is the parameter that is passed to
that function. Therefore the length of the array is the number of times that function will be called.

The config/ subdirectory contains some example configuration files for reference.

#### tests/
Location of the python class files.  Each file should contain a class that inherits from the SystemTest
base class, which inherits from unittest.TestCase.  The functions of these systemtest classes are your system tests.
When you write a new class that inherits from SystemTest, place your python file in this directory.

The tests/ subdirectory contains some example python files for reference.

#### docs/
Location for documentation of the system test class files.

#### output/
Location of the output file(s) produced by running the system tests.  Each run produces a subdirectory based on the
timestamp when the system tests began, and this subdirectory contains an output JSON file for every individual
systemtest that was performed. (Example: "output/2016_11_03_21_46_06/NameOfTestClass")
Note that even if multiple system test classes were configured in the same configuration JSON file, the outputs will
be written to separate files, one for each class.

#### utils/
Location of various files with utility functions. These may be used in system test files or in other utility function
files, such as converting data between JSON format and python dictionary format.
