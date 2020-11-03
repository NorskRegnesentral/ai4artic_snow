import numpy as np
from rasterio.crs import CRS

import rasterio
from rasterio.merge import merge


def to_tiff(filepath, data, transform, no_data_val=None, crs=32633):
    """
    Writes data to a tiff-file
    Args:
        filepath: path of new tiff file
        data:
        transform:
        no_data_val:
        crs:

    """
    if len(data.shape) == 2:
        data = data[:, :, None]

    with rasterio.open(
        filepath,
        "w",
        driver="GTiff",
        compress="lzw",
        bigtiff="YES",
        height=data.shape[0],
        width=data.shape[1],
        count=data.shape[2],
        dtype=data.dtype,
        crs=CRS.from_epsg(crs),
        transform=transform,
        nodata=no_data_val,
    ) as out_file:
        [out_file.write(data[:, :, i], 1 + i) for i in range(data.shape[2])]


def merge_tiff_files(in_files, out_file, no_data_val=None):
    """
    Merge files into one
    Args:
        in_files: list of file paths of files to merge
        out_file: path of out file
        no_data_val:

    Returns:
        merged image

    """

    in_files = [rasterio.open(p) for p in in_files]
    out_meta = in_files[0].meta.copy()
    mosaic, out_trans = merge(in_files, nodata=no_data_val)
    [f.close() for f in in_files]

    out_meta.update(
        {
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_trans,
            "nodata": no_data_val,
        }
    )

    if out_file is not None:
        with rasterio.open(
            out_file,
            "w",
            **out_meta,
        ) as dest:
            dest.write(mosaic)

    return np.moveaxis(mosaic, 0, -1)
