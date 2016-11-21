# BossCutoutSystemTest Reference
## About
System tests for uploading/downloading cutouts via the Boss API. The BossCutoutSystemTest class inherits from the BossSystemTest class. The class configuration expects the below in the configuration JSON file:

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
      "x_start": <int>, /* required */
      "x_stop": <int>, /* required */
      "y_start": <int>, /* required */
      "y_stop": <int>, /* required */
      "z_start": <int>, /* required */
      "z_stop": <int> /* required */
    },
    "experiment": /* required */
    {
      "name": <string>, /* required */
      "num_time_samples": <int> /* required */
    },
    "channel": /* requred, defines Initial/default channel */
    {
      "name": <string>, 
      "datatype": <string> /* required */
    },
    "cutout_read_test:[...],
    "cutout_write_test:[...],
    "cutout_match_test:[...],
    "cutout_read_invalid_test":[...],
    "cutout_write_invalid_test":[...],
    "cutout_read_cache_hit_test":[...],
    "cutout_write_cache_hit_test":[...],
    "cutout_read_throughput_size_test":[...],
    "cutout_write_throughput_size_test":[...],
    "cutout_read_throughput_cache_miss_test":[...],
    "cutout_write_throughput_cache_miss_test":[...]
  }
```

## System test methods
In each test, a list of cutout coordinates along the x, y, z, and/or time axes is generated based on the parameters for that test. For each set of coordinates, the cutout system is used to read (download) or write (create data and upload) from a channel at those coordinates.  The duration of this read or write operation is stored as part of the test result.

---
#### cutout_read_test()
Downloads a single cutout from the channel.

```
"cutout_read_test":[
  {
    "x_range":[<int>, <int>],   /* required */
    "y_range":[<int>, <int>],   /* required */
    "z_range":[<int>, <int>],   /* required */
    "time_range":[<int>, <int>],
    "resolution":<int>,
    "channel":
    {
      "datatype":<string>,
      "name":<string>
    }
  }
]
```
- *x_range* = The cutout's x-axis coordinate range. Format is [start, stop].
- *y_range* = The cutout's y-axis coordinate range. Format is [start, stop].
- *z_range* = The cutout's z-axis coordinate range. Format is [start, stop].
- *time_range* = The cutout's time coordinate range.  If omitted, default is null, otherwise format is [start, stop].
- *resolution* = Data resolution.  If omitted, default is 0.
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.

---
#### cutout_read_invalid_test()
Downloads a single cutout from the channel, but expects an error to occur. The test fails if no error occurs.

```
"cutout_read_invalid_test":[
  {
    "x_range":[<int>, <int>],   /* required */
    "y_range":[<int>, <int>],   /* required */
    "z_range":[<int>, <int>],   /* required */
    "time_range":[<int>, <int>],
    "resolution":<int>,
    "channel":
    {
      "datatype":<string>,
      "name":<string>
    },
    "status":<int>
  }
]
```
- *x_range* = The cutout's x-axis coordinate range. Format is [start, stop].
- *y_range* = The cutout's y-axis coordinate range. Format is [start, stop].
- *z_range* = The cutout's z-axis coordinate range. Format is [start, stop].
- *time_range* = The cutout's time coordinate range.  If omitted, default is null, otherwise format is [start, stop].
- *resolution* = Data resolution.  If omitted, default is 0.
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.
- *status* = Numeric status code of an expected HTTP error.  If given, the test passes only if an error with this status occurs. Otherwise, if omitted, the test passes if any error occurs.

---
#### cutout_write_test()
Creates a data cuboid and uploads it to the channel.


Expects the same parameters as *cutout_read_test()*.

---
#### cutout_write_invalid_test()
Uploads a single cutout to the channel, but expects an error to occur. The test fails if no error occurs.

Expects the same parameters as *cutout_read_invalid_test()*.

---
#### cutout_match_test()
Creates a data cuboid and uploads it to the channel. Then downloads from the same coordinates, and attempts to compare that the data is the same.

Expects the same parameters as *cutout_read_test()*.

---
#### cutout_read_cache_hit_test()
Two consecutive read operations. Records the duration of the second read; after reading once, the second read should be faster because the data is cached.

Expects the same parameters as *cutout_read_test()*.

---
#### cutout_write_cache_hit_test()
Two consecutive write operations. Records the duration of the second write; after writing once, the second write should be faster because the data is cached.


Expects the same parameters as *cutout_read_test()*.

---
#### cutout_read_throughput_size_test()
Sequence of consecutive reads of progressively increasing cutouts. The lower value on each axis stays the same, but the upper value on an axis may increase.  For example, if an axis is given "start:stop:delta", then the ranges will be at [start, start+delta], then [start, start+2xdelta], and so on, up to [start, stop].

Because some of the region is cached on each operation, Boss should encounter a partial cache hit and partial cache miss during the sequence.  The duration of each read is recorded.
```
"cutout_read_throughput_size_test":[
  {
    "x_range":[<int>, <int>] or [<int>, <int>, <int>],   /* required */
    "y_range":[<int>, <int>] or [<int>, <int>, <int>],   /* required */
    "z_range":[<int>, <int>] or [<int>, <int>, <int>],   /* required */
    "time_range":[<int>, <int>] or [<int>, <int>, <int>],
    "resolution":<int>,
    "channel":
    {
      "datatype":<string>,
      "name":<string>
    }
  }
]
```
- *x_range* = The cutout's x-axis coordinate range. Format is [start, stop] for a fixed range, or [start, stop, delta] for a list of incrementing ranges.
- *y_range* = The cutout's y-axis coordinate range. Format is [start, stop] or [start, stop, delta].
- *z_range* = The cutout's z-axis coordinate range. Format is [start, stop] or [start, stop, delta].
- *time_range* = The cutout's time coordinate range.  If omitted, default is null, otherwise format is [start, stop] or [start, stop, delta].
- *resolution* = Data resolution.  If omitted, default is 0.
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.

---
#### cutout_write_throughput_size_test()
Sequence of consecutive uploads of progressively increasing cutouts. The lower value on each axis stays the same, but the upper value on an axis may increase.  For example, if an axis is given "start:stop:delta", then the ranges will be at [start, start+delta], then [start, start+2xdelta], and so on, up to [start, stop].

Because some of the region is cached on each operation, Boss should encounter a partial cache hit and partial cache miss during the sequence.  The duration of each write is recorded.

Expects the same parameters as *cutout_read_throughput_size_test()*.

---
#### cutout_read_throughput_cache_miss_test()
Sequence of consecutive reads of cutouts along one or more coordinate axes. If a "delta" is given for an axis, then each sequential read will shift along that axis by that amount; the size of the cutout is the same.  For example, if an axis is given "start:stop:delta", then the ranges will be at [start, start+delta], then [start+delta, start+2xdelta], and so on, up to [stop-delta, stop].

This test is expected to traverse a large region of the coordinate frame, eventually forcing Boss to encounter a full cache miss. The duration of each read is recorded.
```
"cutout_read_throughput_cache_miss_test":[
  {
    "x_range":[<int>, <int>] or [<int>, <int>, <int>],   /* required */
    "y_range":[<int>, <int>] or [<int>, <int>, <int>],   /* required */
    "z_range":[<int>, <int>] or [<int>, <int>, <int>],   /* required */
    "time_range":[<int>, <int>] or [<int>, <int>, <int>],
    "resolution":<int>,
    "channel":
    {
      "datatype":<string>,
      "name":<string>
    }
  }
]
```
- *x_range* = The cutout's x-axis coordinate range. Format is [start, stop] for a fixed range, or [start, stop, delta] for a list of incrementing ranges.
- *y_range* = The cutout's y-axis coordinate range. Format is [start, stop] or [start, stop, delta].
- *z_range* = The cutout's z-axis coordinate range. Format is [start, stop] or [start, stop, delta].
- *time_range* = The cutout's time coordinate range.  If omitted, default is null, otherwise format is [start, stop] or [start, stop, delta].
- *resolution* = Data resolution.  If omitted, default is 0.
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.

---
#### cutout_write_throughput_cache_miss_test()
Sequence of consecutive uploads of cutouts that translate along one or more coordinate axes. If a "delta" is given for an axis, then each sequential read will shift along that axis by that amount; the size of the cutout is the same.  For example, if an axis is given [start, stop, delta], then the ranges will be at [start, start+delta], then [start+delta, start+2xdelta], and so on, up to [stop-delta, stop].

This test is expected to traverse a large region of the coordinate frame, eventually forcing Boss to encounter a full cache miss. The duration of each write is recorded.

Expects the same parameters as *cutout_read_throughput_cache_miss_test()*.
