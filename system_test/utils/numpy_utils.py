import numpy, re, sys


def cuboid(xsize: int, ysize: int, zsize: int, tsize=None, datatype='uint8', max_bytes=50000000):
    """ Generate a datacube of random numbers. Range of possible values is from 1 up to
    the highest possible value of a numpy datatype.
    Args:
        xsize (int) : Size of the x-dimension
        ysize (int) : Size of the y-dimension
        zsize (int) : Size of the z-dimension
        tsize (int) : Optional, Size of the time dimension (default is 0)
        datatype (str) : Name of the numpy datatype for the data (default is 'uint8')
        max_bytes (int) : Optional, limit on the size of the data in bytes (default is ~50 MB)
    Returns:
        (numpy.ndarray) 4D or 3D array of random numbers, ranging from 1 up to the maximum value of the datatype
    """
    s = re.search('int|float', datatype)
    high = 2 if (not s) else numpy.iinfo(datatype).max if (s.group(0) == 'int') else numpy.finfo(datatype).max
    dims = (zsize, ysize, xsize) if not bool(tsize) else (tsize, zsize, ysize, xsize)
    data = numpy.random.randint(1, high, dims, datatype)
    if bool(max_bytes):
        assert sys.getsizeof(data) <= max_bytes, 'Cuboid size {0} exceeds {1} bytes'.format(data.shape, max_bytes)
    return data


def array_range(values):
    """Convert a list of 3 elements [start, stop, delta] into a range array [start, ..., delta].
        Lists of 2 or fewer elements are unchanged. Inputs that are not lists become arrays.
    Args:
        values : What to convert into an array
    Returns:
        (numpy.ndarray) A list that is at least as long as the input values
    """
    if isinstance(values, (list, tuple, numpy.ndarray)):
        if len(values) < 3:
            vals_out = values  # No change to lists of 0 to 2 elements
        elif len(values) == 3:
            vals_out = numpy.array(range(values[0], values[1] + int(numpy.sign(values[2])), values[2]))
        else:
            raise ValueError('array_range() argument must have 3 or fewer elements.')
    else:
        vals_out = numpy.array([values])  # Make iterable and convert into list
    # print('array_range {0} -> {1}'.format(values, vals_out))
    return vals_out


def array_reduce(values, get_delta=False):
    """Convert a list of 3 or more elements, or a tuple of 2 or more elements, into a shorter array.
        By default, returns only the start and end elements. The get_delta option will include a 3rd value in the
        array, which is an approximation of a constant increment between consecutive elements.
    Args:
        values : A list, tuple, or numpy array with at least 3 elements
        get_delta (Optional) : Boolean to return a 3rd element, default is False
    Returns:
        (numpy.ndarray) : An array of the first and last elements, (and/or the mean increment)
    """
    if isinstance(values, (list, tuple, numpy.ndarray)):
        if len(values) <= 2:
            raise ValueError('array_reduce() argument must have 3 or more elements.')
        else:
            vals_out = [values[0], values[-1]]
            if get_delta and len(values) >= 3:
                vals_out = numpy.append(vals_out, (values[1:] - values[0:-1]).mean())
    else:
        raise TypeError('array_reduce() input must be a list or tuple.')
    return vals_out
