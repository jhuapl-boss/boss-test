# BossImageSystemTest Reference
## About
System tests for downloading images via the Boss API. The BossImageSystemTest class inherits from the BossSystemTest class. The class configuration expects the below in the configuration JSON file:

```
"BossImageSystemTest":
  {
    "version": <float>, /* Boss API version */
    "collection": /* required */
    {
      "name": <string> /* required */
    },
    "coordinate_frame": /* required */
    {
      "name": <string>, /* required */
      "x_start": <integer>, /* required */
      "x_stop": <integer>, /* required */
      "y_start": <integer>, /* required */
      "y_stop": <integer>, /* required */
      "z_start": <integer>, /* required */
      "z_stop": <integer> /* required */
    },
    "experiment": /* required */
    {
      "name": <string>, /* required */
      "max_time_sample": <integer> /* required */
    },
    "channel": /* requred, defines Initial/default channel */
    {
      "name": <string>, /* required */
      "datatype": <string> /* required */
    },
    "image_get_test:[...],
    "image_invalid_test":[...],
    "image_cache_hit_test":[...],
    "image_throughput_size_test":[...],
    "image_cache_miss_throughput_test":[...]
  }
```

## System test methods
In each test, a list of image definitions (coordinates along the x, y, z, and/or time axes) is generated based on the parameters for that test. For each set of indices and image size, the image system is used to read one or more images from a channel at that index.  The duration of this get request is stored as part of the test result.

---
#### image_get_test()
Performs a single get request for a image from the channel.

```
"image_get_test":[
  {
    "orientation":<string>, /* required */
    "x_arg":<integer or string>,   /* required */
    "y_arg":<integer or string>,   /* required */
    "z_arg":<integer or string>,   /* required */
    "t_index":<integer>,
    "resolution":<integer>,
    "accept":<string>,
    "channel":
    {
      "datatype":<string>,
      "name":<string>
    }
  }
]
```
- *orientation* = The image's aligned plane, either "xy", "xz", or "xy".
- *x_arg* = The image's x-axis coordinate(s).  Format is "value" (if flat on this axis) or "start:stop" (if coplanar to this axis).
- *y_arg* = The image's y-axis coordinate(s).  Format is "value" (if flat on this axis) or "start:stop" (if coplanar to this axis).
- *z_arg* = The image's z-axis coordinate(s).  Format is "value" (if flat on this axis) or "start:stop" (if coplanar to this axis).
- *t_index* = The image's time frame index. If omitted, default is null.
- *resolution* = Data resolution.  If omitted, default is 0.
- *accept* = Image file format.  If omitted, default is "image/png".
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.

---
#### image_invalid_test()
Performs a single get request for a image from the channel, but expects an error to occur.  Fails if no error occurs.

```
"image_invalid_test":[
  {
    "orientation":<string>, /* required */
    "x_arg":<integer or string>,   /* required */
    "y_arg":<integer or string>,   /* required */
    "z_arg":<integer or string>,   /* required */
    "t_index":<integer>,
    "resolution":<integer>,
    "accept":<string>,
    "channel":
    {
      "datatype":<string>,
      "name":<string>
    },
    "status":<integer>
  }
]
```
- *orientation* = The image's aligned plane, either "xy", "xz", or "xy".
- *x_arg* = The image's x-axis coordinate(s).  Format is "value" (if flat on this axis) or "start:stop" (if coplanar to this axis).
- *y_arg* = The image's y-axis coordinate(s).  Format is "value" (if flat on this axis) or "start:stop" (if coplanar to this axis).
- *z_arg* = The image's z-axis coordinate(s).  Format is "value" (if flat on this axis) or "start:stop" (if coplanar to this axis).
- *t_index* = The image's time frame index. If omitted, default is null.
- *resolution* = Data resolution.  If omitted, default is 0.
- *accept* = Image file format.  If omitted, default is "image/png".
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.
- *status* = Numeric status code of an expected HTTP error.  If given, the test passes only if an error with this status occurs. Otherwise, if omitted, the test passes if any error occurs.

---
#### image_cache_hit_test()
Performs two consecutive get requests for the same image from the channel. Records the duration of the second get request.

Expects the same parameters as *image_get_test()*.

---
#### image_throughput_size_test()
Sequence of consecutive downloads of progressively increasing images. The lower value on each axis stays the same, but the upper value on an axis may increase.  For example, if an axis is given "start:stop:delta", then the ranges will be at [start, start+delta], then [start, start+2xdelta], and so on, up to [start, stop].

Because some of the region is cached on each operation, Boss should encounter a partial cache hit and partial cache miss during the sequence.  The duration of each read is recorded.

```
"image_throughput_size_test":[
  {
    "orientation":<string>, /* required */
    "x_arg":<integer or string>,   /* required */
    "y_arg":<integer or string>,   /* required */
    "z_arg":<integer or string>,   /* required */
    "t_index":<integer>,
    "resolution":<integer>,
    "accept":<string>,
    "channel":
    {
      "datatype":<string>,
      "name":<string>
    }
  }
]
```
- *orientation* = The image's aligned plane, either "xy", "xz", or "xy".
- *x_arg* = The image's x-axis coordinate(s).  Format is "value" (if flat on this axis) or "start:stop" (if coplanar to this axis) or "start:stop:delta" to increment.
- *y_arg* = The image's y-axis coordinate(s).  Format is either "value", "start:stop", or "start:stop:delta".
- *z_arg* = The image's z-axis coordinate(s).  Format is either "value", "start:stop", or "start:stop:delta".
- *t_index* = The image's time frame index. If omitted, default is null.
- *resolution* = Data resolution.  If omitted, default is 0.
- *accept* = Image file format.  If omitted, default is "image/png".
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.

#### image_throughput_cache_miss_test()
Performs a sequence of requests for different images from the channel, expecting changes in the index along one or more coordinate axes. If a "delta" is given for an axis, then each sequential read will translate along that axis by that amount.  For example, if an axis is given "start:stop:delta", then the index will be move from "start" to "stop", incrementing by "delta".

```
"image_throughput_cache_miss_test":[
  {
    "orientation":<string>, /* required */
    "x_arg":<integer or string>,   /* required */
    "y_arg":<integer or string>,   /* required */
    "z_arg":<integer or string>,   /* required */
    "t_index":<integer or string>,
    "resolution":<integer>,
    "accept":<string>,
    "channel":
    {
      "datatype":<string>,
      "name":<string>
    }
  }
]
```
- *orientation* = The image's aligned plane, either "xy", "xz", or "xy".
- *x_arg* = The image's x-axis coordinate(s).  Format is "value" (if flat on this axis) or "start:stop" (if coplanar to this axis) or "start:stop:delta" to increment.
- *y_arg* = The image's y-axis coordinate(s).  Format is either "value", "start:stop", or "start:stop:delta".
- *z_arg* = The image's z-axis coordinate(s).  Format is either "value", "start:stop", or "start:stop:delta".
- *t_index* = The image's time frame index or indices. Format is either "value" or "start:stop:delta". If omitted, default is null.
- *resolution* = Data resolution.  If omitted, default is 0.
- *accept* = Image file format.  If omitted, default is "image/png".
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.
