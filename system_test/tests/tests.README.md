# tests/

This directory should contain .py files, which define system test classes. Each class should inherit from SystemTest.

## Properties inherited from SystemTest
### parser_args
A namespace made of parsed command line arguments. Should contain the following:
* input_file = Name of the configuration JSON file
* output = Name of the root level of the output directory
~~* version = Boss API version~~
~~* domain = Boss domain name~~

### class_config
A static dictionary variable, loaded from the configuration JSON file, matching the name of the current class. For
example, if the JSON in your configuration file has an object "MyExampleTests":{...}, then "self" in the MyExampleTests
class returns the python dictionary created from this object.

### class_results
A static dictionary variable, used to store the outputs of individual tests. Each key in the dictionary should be the
name of the test, and the value is a list; each element of this list is a test result.
When all of the scheduled tests of a class have completed, the value of class_results will be written to a JSON file
and saved in the output directory.

### test_name
Name of the test method in this SystemTest instance.

### parameters
The input parameters for this individual SystemTest instance. In the class configuration dict, wherever the key is the
name of the current test method, the value of the entry should be a list; each element of this list is the set of
parameters that defines a test.

## Methods inherited from SystemTest
### add_result(result_value)
Called from an individual test, this stores some value into the static class dictionary of test results, where the key
name is the name of the current test method.  To account for multiple parameterizations of the same test method, the
entry for that key is a list, and the result value is appended to that list.
By default, this function is called in a test's *tearDown(self)* method.
