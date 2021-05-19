import logging
from pathlib import Path
import tempfile

import click
import numpy as np
import xarray as xr

from preprocess import conftools as ct
from preprocess.preprocess_reflectance import reflectance
from preprocess.preprocess_reproject import reproject
from preprocess.preprocess_s3import import s3import

_logger = logging.getLogger(__name__)

STEPS = {
    "s3import": s3import,
    "reproject": reproject,
    "reflectance": reflectance,
}


def setup_config():
    cfg = ct.load_directory(Path(__file__).parent / "config")
    cfg = cfg.preprocess
    for d in ("workdir", "tmpdir"):
        cfg[d] = Path(cfg[d])
        cfg[d].mkdir(parents=True, exist_ok=True)
    return cfg


def read_ofile(fpath):
    bands = [
        "S1_reflectance_an",
        "S2_reflectance_an",
        "S3_reflectance_an",
        "S4_reflectance_an",
        "S5_reflectance_an",
        "S6_reflectance_an",
        "S7_BT_in",
        "S8_BT_in",
        "S9_BT_in"
    ]
    with xr.open_dataset(fpath) as ds:
        return [ds[b].values.squeeze() for b in bands], ds.rio.transform()


def preprocess(ifile, cfg, overwrite=False):
    tmpdir = cfg.tmpdir / ifile.stem
    tmpdir.mkdir(parents=True, exist_ok=True)
    for sname, func in STEPS.items():
        _logger.info(sname)
        ofile = cfg.workdir / sname / f"{ifile.stem}.nc"
        if not overwrite and ofile.exists():
            _logger.info("%s exists. Skip", ofile)
            ifile = ofile
            continue
        ofile.parent.mkdir(parents=True, exist_ok=True)
        _logger.debug(ofile)
        with tempfile.TemporaryDirectory(dir=tmpdir, prefix=sname) as tdir:
            ifile = func(ofile, ifile, Path(tdir), cfg['preprocess'][sname])

    ofile = ifile
    return ofile


@click.command()
@click.argument("ifile", type=Path)
@click.option("--overwrite/--no-overwrite", default=False)
def main(ifile, overwrite):
    logging.basicConfig(level="DEBUG")
    logging.getLogger("pyproj").setLevel("DEBUG")
    cfg = setup_config()
    preprocess(ifile, cfg, overwrite)


if __name__ == "__main__":
    main()
