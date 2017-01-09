# SimpleBossImageTest Reference
## About
Simplified tests of the Boss image service. Each test performs a very similar behavior, and requires very few parameters for each test configuration. By contrast, the BossImageSystemTest test configurations use parameters that exactly match the Boss image service API, and specifying the exact axis ranges and increments for each test can be burdensome.

These tests are meant to streamline this process by using "descriptive" parameters rather than quantitative ranges. There are also fewer test functions, because the read, write, cache-hit, and read-write match data are all performed together. Also, each test will inherit default parameters from the "top level" parameters of the class; these tests could be run without specifying any numeric values.

## Test design
Every test first generates a list of coordinates for 4D cuboids. Then it loops through those coordinate sets. For each coordinate set (i.e., one image), it performs 1 write, 1 to 2 reads, and 1 check for consistency. The test will output lists of cuboid sizes, write times, read times, and consistency percentages, which can be visualized as line plots later.

The main loop performs the following:
1. Generate a 4D matrix of random data, and use **remote.create_image** to upload it into the channel at the next set of coordinates. Record the time for this to complete.
2. If there is a delay, then wait. By default the delay is zero.
3. Read data by using **remote.get_image** at the same coordinates. Record the time for this to complete. If the "cache_hit" parameter was given (see below), then 2 reads are performed, and only the second one is timed.
4. Check the consistency between the uploaded and downloaded data, and record the match percentage.

In the list of coordinate sets, each successive cuboid is larger than the previous one. The increment is a constant factor along all 4 dimensions. The starting positions (corner of the cuboid) translate along the x axis, increasing from x=0.

## Class configuration
The SimpleBossImageTest class inherits from the SimpleBossTest class. The class configuration expects the below in the configuration JSON file:

```
{
  "SimpleBossImageTest":
  {
    "unit_size":[<int>, <int>, <int>, <int>],
    "step_size":[<int>, <int>, <int>, <int>],
    "steps": <int>,
    "cache_hit": <boolean>,
    "cuboid_align": <boolean>,
    "delay": <double>,
    "one_image_test":[
      {...},
      {...},
      ...  /* test configurations here */
    ],
    "invalid_image_test":[
      ...  /* test configurations here */
    ],
    "multiple_image_test":[
      ...  /* test configurations here */
    ]
  }
  
```

##Parameters:
* *unit_size* = The dimensions of the first image region. Also the minimum cuboid dimensions. This is a 4-element list, defined as [x, y, z, t]. So the initial cuboid is at coordinates [(0, x), (0, y), (0, z), (0, t)]. By default this is [512, 512, 16, 1].
* *step_size* = The increments in which the cuboids grow along each dimension. By default, this uses the value of *unit_size*.
* *steps* = Number of images in the loop. By default, this is 1.
* *cache_hit* = A flag that causes the tests to perform 2 read operations per loop, and record the duration of the second one. By default, this is false.
* *cuboid_align* = A flag that causes each cuboid start position and dimension to be a multiple of the cache size [512, 512, 16, 1]. Each is rounded up; for example, the range x=(1000, 2000) would be rounded to x=(1024, 2048). By default, this is false.
* *delay* = The time to delay between a write and a read. By default this is 0.


##Test methods
####one_image_test()
Performs the image operations for one image. The *steps* parameter is forced to 1, and so the *step_size* parameter has no effect. The expected parameters and their defaults are otherwise the same parameters listed above.

####multiple_image_test()
Performs one or more loops with the image operations. The expected parameters and their defaults are the same parameters listed above.


####invalid_image_test()
Performs one or more loops with the image operations, but it expects an error or failure to occur during the loop. If nothing went wrong, then the test fails. The expected parameters and their defaults are the same parameters listed above. This test configuration also accepts the following parameters:

* *status* = Status code of the expected HTTP error, if any. If the occurring error is an HTTP error with this matching code, then the test passes. If it is a different error type or has a different code, then the test fails.

## Note about Boss resources
Unlike the BossImageSystemTest tests, the tester does not specify the properties of the resources to create via intern (i.e., naming the collection, coordinate frame, experiment, or channel). The creation and deletion of these resources is meant to be handled by the class, during the *setUpClass* and *tearDownClass* calls.