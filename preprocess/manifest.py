# -*- coding: utf-8 -*-

from contextlib import suppress
import datetime
import fnmatch
from lxml import etree
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon
import zipfile

from preprocess import conftools as ct


def parse_esa_datetime(datestr):
    """Parse datetime strings from ESA Sentinel Products"""
    with suppress(ValueError):
        return datetime.datetime.fromisoformat(datestr)
    with suppress(ValueError):
        dt = datetime.datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    with suppress(ValueError):
        dt = datetime.datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%SZ")
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    raise ValueError(f"Failed to parse '{datestr}'")


def parse(safefile):
    safefile = Path(safefile)
    if safefile.name in ("manifest.safe", "xfdumanifest.xml"):
        safefile = safefile.parent
    meta = parser_s3(safefile)
    meta.identifier = safefile.stem
    meta.missionid = safefile.stem.split("_")[0]
    meta.satellite = meta.missionid
    meta.date = parse_esa_datetime(meta.beginposition).date().isoformat()
    return meta


def parser_s3(safefile):
    root = get_xmltree(safefile)
    meta = ct.Config()
    meta.filename = root.find(".//{*}productName").text
    meta.platformname = root.find(".//{*}familyName").text.capitalize()
    meta.productname = root.find(".//{*}productName").text
    meta.producttype = root.find(".//{*}productType").text
    meta.timeliness = root.find(".//{*}timeliness").text
    meta.beginposition = root.find(".//{*}startTime").text
    meta.endposition = root.find(".//{*}stopTime").text
    meta.footprint, meta.footprint_srs = parse_footprint(root)
    meta.orbitdirection = root.find(".//{*}orbitNumber").attrib["groundTrackDirection"]
    meta.orbitnumber = root.find(".//{*}orbitNumber[@type='start']").text
    meta.relativeorbitnumber = root.find(".//{*}relativeOrbitNumber[@type='start']").text
    meta.passnumber = root.find(".//{*}passNumber[@type='start']").text
    meta.passdirection = root.find(".//{*}passNumber").attrib["groundTrackDirection"]
    meta.relativepassnumber = root.find(".//{*}relativePassNumber[@type='start']").text
    instrelm = root.find(".//{*}instrument")
    meta.instrumentname = instrelm.find(".//{*}familyName").text
    meta.instrumentshortname = instrelm.find(".//{*}familyName").attrib["abbreviation"]
    meta.sensor = meta.instrumentshortname.lower()
    return meta


def parse_footprint(root):
    fpelm = root.find(".//{*}footPrint")
    srsstr = fpelm.attrib["srsName"]
    if "#" in srsstr:
        srs = "EPSG:{}".format(srsstr.split("#")[-1])
    else:
        srs = "EPSG:{}".format(srsstr.split("/")[-1])
    gmlelm = fpelm.find("./")
    gmlstr = fpelm.find("./").text
    if "coordinates" in gmlelm.tag and "," in gmlstr:
        coords = np.array([e.split(",") for e in gmlstr.split()]).astype("float")
    elif "posList" in gmlelm.tag or "," not in gmlstr:
        coords = np.array(gmlstr.split(), dtype="float").reshape(-1, 2)
    coords = np.fliplr(coords)
    return Polygon(coords).wkt, srs


def get_xmltree(safefile):
    safefile = Path(safefile)
    if safefile.name in ("manifest.safe", "xfdumanifest.xml"):
        return etree.parse(str(safefile))
    elif safefile.suffix == ".SAFE":
        return etree.parse(str(safefile / "manifest.safe"))
    elif safefile.suffix == ".SEN3":
        return etree.parse(str(safefile / "xfdumanifest.xml"))
    elif safefile.suffix.lower() == ".zip":
        with zipfile.ZipFile(safefile) as zf:
            members = fnmatch.filter(zf.namelist(), "*manifest.*")
            assert len(members) == 1, (
                "Found {:d} members matching '*manifest.*' in zip".format(len(members)))
            with zf.open(members[0]) as fid:
                return etree.parse(fid)
    raise Exception(f"Failed to parse {safefile}")
