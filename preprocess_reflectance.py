
import datetime
import logging
from pathlib import Path

import numpy as np
import yaml
import xarray as xr

from utils.misc import function_with_exitstack
from utils import xrtools as xrt

_logger = logging.getLogger(__name__)

DOY_TO_SUN_DISTANCE = yaml.load((Path(__file__).parent / "lib/doy_to_sundist.yml").open("r"))
ESUNS = {
  "S1_radiance_an": 1837.39,
  "S2_radiance_an": 1525.94,
  "S3_radiance_an": 956.17,
  "S4_radiance_an": 365.9,
  "S5_radiance_an": 248.33,
  "S6_radiance_an": 78.33
}


def get_solar_distance(date):
    doy = date.timetuple().tm_yday
    return DOY_TO_SUN_DISTANCE[doy]


def get_esun(bandname):
    return ESUNS[bandname]


def convert_rad2refl(data, esun, solar_zenith, solar_dist):
    d2 = solar_dist**2
    refl = (np.pi * data * d2) / (esun * xr.ufuncs.cos(solar_zenith))
    #  refl = (np.pi * data * d2) / (esun * np.cos(np.pi*solar_zenith/180.0))
    refl = xr.where(xr.ufuncs.fabs(solar_zenith-90) < 1e-3, np.inf, refl)
    return refl


@function_with_exitstack()
def calculate_reflectance(stack, ofile, ifile, cfg):
    ids = stack.enter_context(xr.open_dataset(ifile, cache=False))

    date = datetime.date.fromisoformat(ids.source_meta.attrs["date"])
    solar_dist = get_solar_distance(date)
    solar_zenith = xr.ufuncs.deg2rad(ids[cfg.solar_zenith_band])

    for varname in ids.data_vars:
        try:
            esun = get_esun(varname)
        except KeyError as ke:
            _logger.info("Skip variable: %s", varname)
            ods = ids[varname].to_dataset(name=varname)
        else:
            _logger.info("Convert variable: %s", varname)
            oda = convert_rad2refl(ids[varname], esun, solar_zenith, solar_dist)
            oda = xrt.auto_encoding(oda)
            ods = oda.to_dataset(name=varname.replace("radiance", "reflectance"))

        ods.to_netcdf(ofile, "a")


def reflectance(ofile, ifile, tmpdir, cfg):
    tfile = tmpdir / ofile.name
    with xr.open_dataset(ifile) as ids:
        ods = xr.Dataset(attrs=ids.attrs)
        ods.attrs["title"] = "Reflectance Sentinel-3"
        xrt.append_history(ods, "NR S3Reflectance"),
        ods["source_meta"] = ids.source_meta
        ods.to_netcdf(tfile)

    calculate_reflectance(tfile, ifile, cfg)

    tfile.rename(ofile)
    _logger.debug("Written %s", ofile)
    return ofile
