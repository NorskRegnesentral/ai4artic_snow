# Copied from  https://github.com/DHI-GRAS/creodias-finder (uder MIT license)
import os
import shutil
from pathlib import Path
import concurrent.futures
from multiprocessing.pool import ThreadPool

import requests
from tqdm import tqdm


DIRNAME = os.path.dirname(os.path.abspath(__file__))

try:
    with open(os.path.join(DIRNAME,'..','creodias_credentials.txt')) as f:
        lines = f.readlines()
        user, password = lines[0:2]
        user = user.strip('\n').strip('\b')
        password = password.strip('\n').strip('\b')
except:
    raise Exception('Could not read login-credentials for creodias.eu. These should be stored in "creodias_credentials.txt". See README.md for more instructions.')


DOWNLOAD_URL = "https://zipper.creodias.eu/download"
TOKEN_URL = "https://auth.creodias.eu/auth/realms/DIAS/protocol/openid-connect/token"


def _get_token(username, password):
    token_data = {
        "client_id": "CLOUDFERRO_PUBLIC",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    response = requests.post(TOKEN_URL, data=token_data).json()
    try:
        return response["access_token"]
    except KeyError:
        raise RuntimeError(f"Unable to get token. Response was {response}")


def download(uid,  outfile, show_progress=True):
    """Download a file from CreoDIAS to the given location

    Parameters
    ----------
    uid:
        CreoDIAS UID to download
    username:
        Username
    password:
        Password
    outfile:
        Path where incomplete downloads are stored
    """
    token = _get_token(user, password)
    url = f"{DOWNLOAD_URL}/{uid}?token={token}"
    _download_raw_data(url, outfile, show_progress)


def _download_raw_data(url, outfile, show_progress):
    """Downloads data from url to outfile.incomplete and then moves to outfile"""
    outfile_temp = str(outfile) + ".incomplete"
    try:
        downloaded_bytes = 0
        with requests.get(url, stream=True, timeout=100) as req:
            with tqdm(unit="B", unit_scale=True, disable=not show_progress) as progress:
                chunk_size = 2 ** 20  # download in 1 MB chunks
                with open(outfile_temp, "wb") as fout:
                    for chunk in req.iter_content(chunk_size=chunk_size):
                        if chunk:  # filter out keep-alive new chunks
                            fout.write(chunk)
                            progress.update(len(chunk))
                            downloaded_bytes += len(chunk)
        shutil.move(outfile_temp, outfile)
    finally:
        try:
            Path(outfile_temp).unlink()
        except OSError:
            pass

import datetime
from six.moves.urllib.parse import urlencode
from six import string_types

import requests
import dateutil.parser
from shapely.geometry import shape

import re

API_URL = (
    "http://finder.creodias.eu/resto/api/collections/{collection}"
    "/search.json?maxRecords=1000"
)
ONLINE_STATUS_CODES = "34|37|0"


def query(
    collection,
    start_date=None,
    end_date=None,
    geometry=None,
    status=ONLINE_STATUS_CODES,
    **kwargs,
):
    """Query the EOData Finder API
    Parameters
    ----------
    collection: str, optional
        the data collection, corresponding to various satellites
    start_date: str or datetime
        the start date of the observations, either in iso formatted string or datetime object
    end_date: str or datetime
        the end date of the observations, either in iso formatted string or datetime object
        if no time is specified, time 23:59:59 is added.
    geometry: WKT polygon or object impementing __geo_interface__
        area of interest as well-known text string
    status : str
        allowed online/offline statuses (|-separated for OR)
    **kwargs
        Additional arguments can be used to specify other query parameters,
        e.g. productType=L1GT
        See https://creodias.eu/eo-data-finder-api-manual for a full list
    Returns
    -------
    dict[string, dict]
        Products returned by the query as a dictionary with the product ID as the key and
        the product's attributes (a dictionary) as the value.
    """
    query_url = _build_query(
        API_URL.format(collection=collection),
        start_date,
        end_date,
        geometry,
        status,
        **kwargs,
    )

    query_response = {}
    while query_url:
        response = requests.get(query_url)
        response.raise_for_status()
        data = response.json()
        for feature in data["features"]:
            query_response[feature["id"]] = feature
        query_url = _get_next_page(data["properties"]["links"])
    return query_response


def _build_query(
    base_url, start_date=None, end_date=None, geometry=None, status=None, **kwargs
):
    query_params = {}

    if start_date is not None:
        start_date = _parse_date(start_date)
        query_params["startDate"] = start_date.isoformat()
    if end_date is not None:
        end_date = _parse_date(end_date)
        end_date = _add_time(end_date)
        query_params["completionDate"] = end_date.isoformat()

    if geometry is not None:
        query_params["geometry"] = _parse_geometry(geometry)

    if status is not None:
        query_params["status"] = status

    for attr, value in sorted(kwargs.items()):
        value = _parse_argvalue(value)
        query_params[attr] = value

    url = base_url
    if query_params:
        url += f"&{urlencode(query_params)}"

    return url


def _get_next_page(links):
    for link in links:
        if link["rel"] == "next":
            return link["href"]
    return False


def _parse_date(date):
    if isinstance(date, datetime.datetime):
        return date
    elif isinstance(date, datetime.date):
        return datetime.datetime.combine(date, datetime.time())
    try:
        return dateutil.parser.parse(date)
    except ValueError:
        raise ValueError(
            "Date {date} is not in a valid format. Use Datetime object or iso string"
        )


def _add_time(date):
    if date.hour == 0 and date.minute == 0 and date.second == 0:
        date = date + datetime.timedelta(hours=23, minutes=59, seconds=59)
        return date
    return date


def _tastes_like_wkt_polygon(geometry):
    try:
        return geometry.replace(", ", ",").replace(" ", "", 1).replace(" ", "+")
    except Exception:
        raise ValueError("Geometry must be in well-known text format")


def _parse_geometry(geom):
    try:
        # If geom has a __geo_interface__
        return shape(geom).wkt
    except AttributeError:
        if _tastes_like_wkt_polygon(geom):
            return geom
        raise ValueError(
            "geometry must be a WKT polygon str or have a __geo_interface__"
        )


def _parse_argvalue(value):
    if isinstance(value, string_types):
        value = value.strip()
        if not any(
            value.startswith(s[0]) and value.endswith(s[1])
            for s in ["[]", "{}", "//", "()"]
        ):
            value.replace(" ", "+")
        return value
    elif isinstance(value, (list, tuple)):
        # Handle value ranges
        if len(value) == 2:
            value = "[{},{}]".format(*value)
            return value
        else:
            raise ValueError(
                "Invalid number of elements in list. Expected 2, received "
                "{}".format(len(value))
            )
    else:
        raise ValueError(
            "Additional arguments can be either string or tuple/list of 2 values"
        )
