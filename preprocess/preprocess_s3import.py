
import fnmatch
import logging
import xarray as xr
import zipfile

import preprocess.manifest as manifest
import preprocess.xrtools as xrt
from preprocess.misc import function_with_exitstack


_logger = logging.getLogger(__name__)


@function_with_exitstack()
def s3import(stack, ofile, ifile, tmpdir, cfg):
    def _extract_files(tmpdir, zf, products):
        for ncfmt, bfmt in products.items():
            for ncf in fnmatch.filter(zf.namelist(), f"*/{ncfmt}"):
                if (tmpdir / ncf).exists():
                    continue
                _logger.debug("Extract %s", ncf)
                zf.extract(ncf, str(tmpdir))

    def _import_products(ofile, safedir, products, correction_factors):
        for ncfmt, bfmts in products.items():
            for ncf in sorted(safedir.rglob(ncfmt)):
                _logger.debug("Read %s", ncf.name)
                ds = stack.enter_context(xr.open_dataset(ncf))
                group = "{rows}x{columns}".format(**ds.dims)
                ods = xr.Dataset()
                ods.attrs.update(ds.attrs)
                for bfmt in bfmts:
                    for varname in fnmatch.filter(ds.variables, bfmt):
                        cf = correction_factors.get(varname, 1)
                        ods[varname] = ds[varname] * cf
                        ods[varname].attrs = ds[varname].attrs
                ods.to_netcdf(ofile, "a", group=group)

    filemeta = manifest.parse(ifile)

    sensor = filemeta.instrumentshortname.lower()
    products = cfg.products[sensor]
    correction_factors = cfg.correction_factors[sensor]

    if ifile.is_dir():
        # Assume unzipped S3 file
        safedir = ifile
    else:
        # Unzip zip file
        with zipfile.ZipFile(ifile) as zf:
            _extract_files(tmpdir, zf, products)
        safedir = tmpdir / ifile.with_suffix(".SEN3").name

    ds = xr.Dataset()
    xrt.create_attr_variable(ds, "source_meta", filemeta)
    xrt.set_global_cf_attrs(
        ds,
        title="Imported Sentinel-3 files",
        source="ESA SciHub",
        history="NR S3Import"
    )
    tfile = tmpdir / ofile.name
    ds.to_netcdf(tfile)

    _import_products(tfile, safedir, products, correction_factors)
    tfile.rename(ofile)
    return ofile
