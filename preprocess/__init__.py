"""
This package contains code to preprocess .SEN3 files to get arrays with reflectance values (which is used by the deep learning models)
"""
from pathlib import Path

from preprocess.conftools import Config
from preprocess.preprocess import preprocess, read_ofile
import os

def convert_sen3(sen3_file, epsg):
    """
    Convert sentinel3 data to reflectance
    Args:
        sen3_file:
        epsg:

    Returns:
        tuple with data bands as M x N np.arrays:
        (
            S1_reflectance_an,
            S2_reflectance_an,
            S3_reflectance_an,
            S4_reflectance_an,
            S5_reflectance_an,
            S6_reflectance_an,
            S7_BT_in,
            S8_BT_in,
            S9_BT_in,
        )
        Affine transform

    """
    sen3_file = Path(sen3_file)
    cfg = conftools.load_directory(Path(__file__).parent / "config")
    cfg['workdir'] = sen3_file.parents[0]
    cfg['tmpdir'] = sen3_file.parents[0]
    ofile = preprocess(sen3_file, cfg, overwrite=False)

    data_channels, s3_transform = read_ofile(ofile)

    #Todo: remove tmp-file

    return data_channels, s3_transform
