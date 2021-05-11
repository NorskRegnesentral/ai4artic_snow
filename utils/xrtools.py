# -*- coding: utf-8 -*-

from contextlib import suppress, contextmanager
import datetime
import logging
from pathlib import Path

import numpy as np
import pyproj
import rasterio as rio
import rioxarray
import xarray as xr

from .misc import iso_timestamp


logger = logging.getLogger(__name__)


def to_netcdf(ds, path, temp_suffix=".tmp"):
    tmpf = Path(path).with_suffix(temp_suffix)
    ds.to_netcdf(tmpf)
    tmpf.rename(path)
    return path


def auto_encoding(da, dtype="uint16", zlib=True, complevel=4, clear_encoding=True, **kwargs):
    if clear_encoding:
        da.encoding = {}
    dtype_max = np.iinfo(dtype).max
    dtype_min = np.iinfo(dtype).min
    data_max = float(da.max())
    data_min = float(da.min())
    fill_value = dtype_max
    n_vals = dtype_max - dtype_min - 1
    if data_max != data_min:
        scale = (data_max - data_min)/(n_vals)
        offset = data_min - dtype_min/scale
    else:
        scale = 1
        offset = 0
    da.encoding.update({
        "dtype": dtype,
        "scale_factor": scale,
        "add_offset": offset,
        "_FillValue": fill_value,
        "zlib": zlib,
        "complevel": complevel
    })
    da.encoding.update(kwargs)
    with suppress(KeyError):
        del da.attrs["_FillValue"]
    return da


def set_global_cf_attrs(
    ds,
    title,
    source,
    timestamp=None,
    history=None,
    institution=None,
    references="",
    comment="",
    conventions="CF-1.8",
    **kwargs
):
    timestamp = timestamp if timestamp is not None else iso_timestamp()
    institution = institution or "Norwegian Computing Center"
    ds.attrs.update(
        title=title,
        date_created=timestamp,
        source=source,
        institution=institution,
        references=references,
        comment=comment,
        Conventions=conventions,
        **kwargs
    )
    if history is not None:
        append_history(ds, history, timestamp)
    return ds


def create_attr_variable(ds, name, attrs):
    ds[name] = xr.Variable((), np.array(0, dtype="uint8"), attrs=attrs)
    return ds


def append_history(ds, entry, timestamp=None):
    timestamp = timestamp if timestamp is not None else iso_timestamp()
    history = list(filter(None, ds.attrs.get("history", "").split("\n")))
    history.append("{}: {}".format(timestamp, entry))
    ds.attrs["history"] = "\n".join(history)
    return ds


def get_human_readable_resolution(ds):
    """Get human readable resolution string

    Returns a human readable resolution string.
    I.e "1 km", "500 m" or "0.1 deg".

    Requires the resolution to be available by 'rioxarray'

    Parameters
    ----------
        ds : xr.DataSet
            The dataset to read the resolution from.

    Returns
    -------
        str
            The string with the human readable resolution
    """
    res = ds.rio.resolution()[0]
    if ds.rio.crs.is_geographic:
        units = "deg"
    else:
        units = ds.rio.crs.linear_units[0]
        if res >= 1000:
            res = res/1000
            units = f"k{units}"
    if int(res) == res:
        res = int(res)
    return f"{res} {units}"


def write_crs_cf(ds, crs=None, grid_mapping_name="crs"):
    crs = pyproj.CRS(
        crs if crs is not None else ds.rio.crs.to_wkt()
    )
    crs_cf = crs.to_cf()
    with suppress(KeyError):
        del ds.coords["spatial_ref"]
    ds.rio.write_crs(crs, grid_mapping_name=grid_mapping_name, inplace=True)
    ds[grid_mapping_name].attrs = crs_cf
    if crs.is_geographic:
        if "x" in ds:
            ds = ds.rename({"x": "longitude"})
        if "y" in ds:
            ds = ds.rename({"y": "latitude"})

        ds["longitude"].attrs.update(
            standard_name="longitude",
            units="degree_east")
        ds["latitude"].attrs.update(
            standard_name="latitude",
            units="degree_north")
    elif crs.is_projected:
        ds["x"].attrs.update(
            standard_name="projection_x_coordinate",
            long_name="Easting",
            units="m")
        ds["y"].attrs.update(
            standard_name="projection_x_coordinate",
            long_name="Northing",
            units="m")
    else:
        logger.warning("CRS not geographic nor geocentric. Cannot set dim info")
    return ds


@contextmanager
def open_rasterio(fn, name=None, write_crs=True, **kwargs):
    with rioxarray.open_rasterio(fn, masked=True, mask_and_scale=True, **kwargs) as da:
        if write_crs:
            da = write_crs_cf(da)
        if name is None:
            yield da
        else:
            yield da.to_dataset(name=name)


def write_gtiff(fn, da, colormap=None, nodata=None):
    kwargs = {
        "driver": "GTiff",
        "count": 1,
        "dtype": "uint8",
        "transform": da.rio.transform(),
        "crs": da.rio.crs,
        "compress": "LZW",
    }
    for coord in ("x", "lat", "latitude"):
        if coord in da.coords:
            kwargs["width"] = da[coord].size
            break
    assert "width" in kwargs, "Width coordinate not found!"
    for coord in ("y", "lon", "longitude"):
        if coord in da.coords:
            kwargs["height"] = da[coord].size
            break
    assert "height" in kwargs, "Height coordinate not found!"
    if nodata is not None:
        kwargs["nodata"] = nodata

    with rio.open(fn, "w", **kwargs) as ds:
        ds.write_colormap(1, colormap)
        ds.write(da.values.squeeze(), 1)
