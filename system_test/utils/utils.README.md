# tests/
Various utility files and functions that may be useful.

##Boss test utils
Contains functions for creating, accessing, and cleaning up Boss resources. Purpose is to streamline processes that make multiple calls to the Intern and Requests libraries.

##JSON utils
Contains functions for converting from raw JSON files to ordered dictionaries, and vice versa.

##NumPy utils
Contains functions for generating cuboids (3D or 4D). Also has functions that parse and "expand" 3-element lists into full numerical arrays, and vice versa. This is useful for classes like BossCutoutSystemTest, which take 2 or 3 element lists as parameters to represent positions along a coordinate axis.

##Plot utils
Used for analyzing results of tests that had produced array data. It searches through the output JSON and locates a "plot keyword" to signify that the test results should be put into a line graph (for example, plot upload time versus upload data size). Can be called from command line as:

`python plot_utils.py <tests output file with array data>.json`

Requires matplotlib.