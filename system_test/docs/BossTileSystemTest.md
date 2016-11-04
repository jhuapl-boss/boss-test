# BossTileSystemTest Reference
## About
System tests for downloading tiles via the Boss API. The BossTileSystemTest class inherits from the BossSystemTest class. The class configuration expects the below in the configuration JSON file:

```
"BossTileSystemTest":
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
    "tile_get_test:[...],
    "tile_invalid_test":[...],
    "tile_cache_hit_test":[...],
    "tile_throughput_size_test":[...],
    "tile_cache_miss_throughput_test":[...]
  }
```

## System test methods
In each test, a list of tile definitions (indices along the x, y, z, and/or time axes, and tile size) is generated based on the parameters for that test. For each set of indices and tile size, the tile system is used to read one or more tiles from a channel at that index.  The duration of this get request is stored as part of the test result.

---
#### tile_get_test()
Performs a single get request for a tile from the channel.

```
"tile_get_test":[
  {
    "tile_size":<integer>, /* required */
    "orientation":<string>, /* required */
    "x_idx":<integer>,   /* required */
    "y_idx":<integer>,   /* required */
    "z_idx":<integer>,   /* required */
    "t_idx":<integer>,
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
- *tile_size* = Coordinate scale (pixel dimensions) of a tile's width.
- *orientation* = The tile's aligned plane, either "xy", "xz", or "xy".
- *x_idx* = The tile's x-axis index.
- *y_idx* = The tile's y-axis index.
- *z_idx* = The tile's z-axis index.
- *t_idx* = The tile's time frame index. If omitted, default is null.
- *resolution* = Data resolution.  If omitted, default is 0.
- *accept* = Image file format.  If omitted, default is "image/png".
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.

---
#### tile_invalid_test()
Performs a single get request for a tile from the channel, but expects an error to occur.  Fails if no error occurs.

```
"tile_invalid_test":[
  {
    "tile_size":<integer>, /* required */
    "orientation":<string>, /* required */
    "x_idx":<integer>,   /* required */
    "y_idx":<integer>,   /* required */
    "z_idx":<integer>,   /* required */
    "t_idx":<integer>,
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
- *tile_size* = Coordinate scale (pixel dimensions) of a tile's width.
- *orientation* = The tile's aligned plane, either "xy", "xz", or "xy".
- *x_idx* = The tile's x-axis index.
- *y_idx* = The tile's y-axis index.
- *z_idx* = The tile's z-axis index.
- *t_idx* = The tile's time frame index. If omitted, default is null.
- *resolution* = Data resolution.  If omitted, default is 0.
- *accept* = Image file format.  If omitted, default is "image/png".
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.
- *status* = Numeric status code of an expected HTTP error.  If given, the test passes only if an error with this status occurs. Otherwise, if omitted, the test passes if any error occurs.

---
#### tile_cache_hit_test()
Performs two consecutive get requests for the same tile from the channel. Records the duration of the second get request.

Expects the same parameters as *tile_get_test()*.

---
#### tile_throughput_size_test()
Performs a sequence of requests for different tiles from the channel. Expects a range for "tile_size", such that each consecutive request is for a larger-sized tile. The format for "tile_size" is "start:stop:delta", where "start" is the initial tile size, delta is the increment in tile size, and "stop" is the final tile size.

If a "delta" is given for an axis, then each sequential read will translate along that axis by that amount.  For example, if an axis is given "start:stop:delta", then the index will be move from "start" to "stop", incrementing by "delta".

```
"tile_throughput_size_test":[
  {
    "tile_size":<string>, /* required */
    "orientation":<string>, /* required */
    "x_idx":<integer>,   /* required */
    "y_idx":<integer>,   /* required */
    "z_idx":<integer>,   /* required */
    "t_idx":<integer>,
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
- *tile_size* = Coordinate scale (pixel dimensions) of a tile's width. Format is "start:stop:delta" for a list of sizes.
- *orientation* = The tile's aligned plane, either "xy", "xz", or "xy".
- *x_idx* = The tile's x-axis index.
- *y_idx* = The tile's y-axis index.
- *z_idx* = The tile's z-axis index.
- *t_idx* = The tile's time frame index. If omitted, default is null.
- *resolution* = Data resolution.  If omitted, default is 0.
- *accept* = Image file format.  If omitted, default is "image/png".
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.

#### tile_throughput_cache_miss_test()
Performs a sequence of requests for different tiles from the channel, expecting changes in the index along one or more coordinate axes. If a "delta" is given for an axis, then each sequential read will translate along that axis by that amount.  For example, if an axis is given "start:stop:delta", then the index will be move from "start" to "stop", incrementing by "delta".

```
"tile_throughput_cache_miss_test":[
  {
    "tile_size":<integer>, /* required */
    "orientation":<string>, /* required */
    "x_idx":<integer or string>,   /* required */
    "y_idx":<integer or string>,   /* required */
    "z_idx":<integer or string>,   /* required */
    "t_idx":<integer or string>,
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
- *tile_size* = Coordinate scale (pixel dimensions) of a tile's width.
- *orientation* = The tile's aligned plane, either "xy", "xz", or "xy".
- *x_idx* = The tile's x-axis index or indices. Format is "start:stop:delta" for a list of indices.
- *y_idx* = The tile's y-axis index or indices.
- *z_idx* = The tile's z-axis index or indices.
- *t_idx* = The tile's time frame index or indices. If omitted, default is null.
- *resolution* = Data resolution.  If omitted, default is 0.
- *accept* = Image file format.  If omitted, default is "image/png".
- *channel* = Parameters for setting up a new channel for one system test instance.  If omitted, the class's default channel is used.
