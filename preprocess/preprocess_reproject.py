#! /usr/bin/env python

import logging
import multiprocessing as mp
import warnings

import attr
import netCDF4
import numpy as np
import pyproj
from pyresample.geometry import SwathDefinition, AreaDefinition
from pyresample.bilinear.xarr import XArrayBilinearResampler
from scipy.interpolate import LinearNDInterpolator
import shapely
import shapely.ops
import xarray as xr
import rioxarray  # noqa

from preprocess import xrtools as xrt

warnings.filterwarnings("ignore", ".*divide by zero.*")
warnings.filterwarnings("ignore", ".*invalid value encountered.*")
warnings.filterwarnings("ignore", ".*elementwise comparison failed.*")
warnings.filterwarnings("ignore", ".*converting to a PROJ string.*")

_logger = logging.getLogger(__name__)


@attr.s
class LinearResampler:
    srcdef = attr.ib()
    tgtdef = attr.ib()

    def resample(self, da):
        trans = pyproj.transformer.Transformer.from_crs(
            "EPSG:4326", self.tgtdef.crs, always_xy=True
        )
        lats = self.srcdef.lats.values.ravel()
        lons = self.srcdef.lons.values.ravel()
        data = np.ma.masked_invalid(da.values)
        interpolator = LinearNDInterpolator(
            trans.transform(lons, lats), data.ravel(), fill_value=np.nan
        )
        odata = interpolator(*self.tgtdef.get_proj_coords())
        height, width = odata.shape
        if self.tgtdef.crs.is_geographic:
            dims = ("latitude", "longitude")
        else:
            dims = ("y", "x")

        coord_x, coord_y = self.tgtdef.get_proj_vectors()
        coords = {
            dims[0]: coord_y,
            dims[1]: coord_x
        }
        da = xr.DataArray(
            np.ma.masked_invalid(odata).filled(np.nan),
            coords=coords,
            dims=dims,
            attrs=da.attrs
        )
        return da


def get_netcdf_contents(ifile):
    _logger.info("Fetching ncfile contents")
    contents = {}
    with netCDF4.Dataset(ifile) as ds:
        for gname, grp in ds.groups.items():
            for vname in grp.variables.keys():
                contents.setdefault(gname, []).append(vname)
            _logger.debug(contents[gname])
    return contents


def get_extent(ifile, contents, cfg):
    extents = []
    for grp, vars in contents.items():
        _logger.debug(grp)
        latvar = [v for v in vars if "latitude" in v][0]
        lonvar = [v for v in vars if "longitude" in v][0]

        with xr.open_dataset(ifile, group=grp) as ids:
            lats, lons = ids[latvar], ids[lonvar]
            srcres = list(map(int, ids.resolution.strip("[]").split()))

        # Ignore extent of solar* bands and other bands with very unequal resolution
        if max(srcres) / min(srcres) > 4:
            continue

        trans = pyproj.transformer.Transformer.from_crs("EPSG:4326", cfg.crs, always_xy=True)

        xarr, yarr = trans.transform(lons.values, lats.values)
        xarr, yarr = np.ma.masked_invalid(xarr), np.ma.masked_invalid(yarr)
        extents.append(shapely.geometry.box(
            xarr.min(),
            yarr.min(),
            xarr.max(),
            yarr.max()
        ))
        _logger.debug(extents[-1].bounds)

    extent = shapely.ops.unary_union(extents).bounds
    extent = np.concatenate(
        (np.floor(np.array(extent[:2]) / cfg.resolution)*cfg.resolution,
         np.ceil(np.array(extent[2:]) / cfg.resolution)*cfg.resolution)
    )
    extent += (-cfg.resolution, -cfg.resolution, cfg.resolution, cfg.resolution)

    if pyproj.CRS(cfg.crs).is_geographic:
        extent = np.clip(extent, (-180, -90, -180, -90), (180, 90, 180, 90))

    width = int(np.rint((extent[2] - extent[0]) * 1.0 / cfg.resolution))
    height = int(np.rint((extent[3] - extent[1]) * 1.0 / cfg.resolution))
    _logger.debug("w, h: %d, %d", width, height)

    if width*height > 1e8:
        raise Exception(f"Output dimension is too large: {height}x{width}")
    cfg.extent = extent
    return extent


def pad_dataset(ods, cfg):
    ds_bounds = ods.rio.bounds()
    ds_xmin, ds_xmax = sorted(ds_bounds[slice(0, 4, 2)])
    ds_ymin, ds_ymax = sorted(ds_bounds[slice(1, 4, 2)])
    if (ds_xmin < (cfg.extent[0] + cfg.resolution) and
            ds_xmax > (cfg.extent[2] - cfg.resolution) and
            ds_ymin < (cfg.extent[1] + cfg.resolution) and
            ds_ymax > (cfg.extent[3] - cfg.resolution)):
        return ods
    return ods.rio.pad_box(*cfg.extent)


def create_areadef(extent, cfg, tileno=0):
    height = int((extent[3]-extent[1]) / cfg.resolution)
    width = int((extent[2]-extent[0]) / cfg.resolution)
    _logger.debug("Area extent: %s", extent)
    return AreaDefinition.from_extent(
        area_id=f"{tileno:04d}",
        projection=cfg.crs,
        shape=(height, width),
        area_extent=extent,
        nprocs=cfg.get("nprocs", mp.cpu_count())
    )


def get_resampler(ifile, grp, vars, cfg):
    with xr.open_dataset(ifile, group=grp) as ds:
        ds = ds.rename_dims(rows="y", columns="x")
        lat = ds[[v for v in vars if "latitude" in v][0]]
        lon = ds[[v for v in vars if "longitude" in v][0]]
        srcdef = SwathDefinition(lats=lat, lons=lon)
        srcres = list(map(int, ds.resolution.strip("[]").split()))

    areadef = create_areadef(cfg.extent, cfg)
    if max(srcres) > 4*min(srcres):
        return LinearResampler(srcdef, areadef)
    resampler = XArrayBilinearResampler(srcdef, areadef, 10*max(srcres))
    return resampler


def reproject_group(ofile, ifile, grp, vars, cfg):
    _logger.info("Reproject group")
    dims = ("latitude", "longitude") if pyproj.CRS(cfg.crs).is_geographic else ("y", "x")
    chunk_size = cfg.get("chunk_size", 1000)

    resampler = get_resampler(ifile, grp, vars, cfg)

    for var in vars:
        print(var)
        if "latitude" in var or "longitude" in var:
            _logger.debug("Skipping: %s", var)
            continue
        chunks = dict(rows=chunk_size, columns=chunk_size)
        with xr.open_dataset(ifile, group=grp, chunks=chunks) as ids:
            ids = ids.rename_dims(rows="y", columns="x")
            _logger.info("Reproject %s / %s", grp, var)

            ida = ids[var]
            if ida.units == "degrees":
                ida = ida.where(ida <= 360)

            oda = resampler.resample(ida)
            oda = oda.rename(y=dims[0], x=dims[1])
            oda = oda.rename(var)
            oda.attrs.update(ids[var].attrs)
            # oda = xrt.write_crs_cf(oda, crs=cfg.crs)
            oda = xrt.auto_encoding(oda, dtype="uint16")
            oda = oda.expand_dims(band=1)

            ods = oda.to_dataset(name=var)
            ods.to_netcdf(ofile, "a")

        _logger.info("Completed reprojecting %s / %s", grp, var)
    _logger.info("Completed reprojecting %s", grp)


def reproject(ofile, ifile, tmpdir, cfg):
    _logger.info("Reproject %s", ifile)
    tfile = tmpdir / ofile.name
    with xr.open_dataset(ifile) as ids:
        ods = xr.Dataset(attrs=ids.attrs)
        ods.attrs["title"] = "Resampled Sentinel-3"
        xrt.append_history(ods, "NR S3Resample")
        ods["source_meta"] = ids.source_meta
        ods.to_netcdf(tfile)

    contents = get_netcdf_contents(ifile)
    get_extent(ifile, contents, cfg)
    for grp, vars in contents.items():
        reproject_group(tfile, ifile, grp, vars, cfg)

    tfile.rename(ofile)
    _logger.info("Written %s", ofile)
    _logger.info("Reproject complete")
    return ofile
