"""
Module with functions to work with API from www.eocloud.eu.
"""

import binascii
import os

import json
from urllib.error import HTTPError

import multiprocessing

import urllib
import wget
import zipfile

from datetime import date
import requests

def download_sentinel_data(  eodata_path, output_location, verbose=1, timeout=10 * 60, debug=False ):
    """
    Download and unzip a tile with satelite data.

    Args:
        product_identifier (string): Product identifier
        output_location (string): Location of where to put unzip output data
        verbose (int): Print progress (verbose==1)
        timeout (int): seconds to timeout wget. On timeout download is restarted up to 10 times
        debug (bool): run on main thread if set to True (timeout is ignored)

    Returns:
        string: Path to SAFE-folder
    """

    tmp_zip_file = os.path.join(
        output_location,
        str(os.getpid()) + "_" + str(binascii.hexlify(os.urandom(16))) + "_tmp.zip",
    )
    product_identifier = eodata_path.split('/')[-1]
    safe_file = os.path.join(output_location, product_identifier + ".SAFE")

    url = "http://185.48.233.249/" + eodata_path.split('eodata/')[-1]
    if verbose:
        print("Downloading", product_identifier, url)

    # Download
    # We need to do this async as it sometimes freezes
    def _download(n_retries=0):
        try:
            wget.download(
                url,
                out=tmp_zip_file,
                bar=wget.bar_thermometer if verbose else None,
            )
        except Exception as e:
            if n_retries:
                _download(n_retries - 1)
            else:
                raise e

    n_retries = 5
    if not debug:
        i = 0
        completed = False
        while i < n_retries and not completed:
            i += 1

            p = multiprocessing.Process(target=_download, daemon=True)
            p.start()
            p.join(timeout=timeout)
            if p.is_alive():
                p.terminate()
                p.join()
                print("Retrying download.", n_retries - i, "retries left.")
                continue
            completed = True

        if not completed:
            raise TimeoutError("Download reached timeout ten times.")

    else:
        _download(n_retries)

    if verbose:
        print("\n")

    if not os.path.isdir(output_location):

        if verbose:
            print("Making directory:", output_location)

        os.makedirs(output_location)

    if verbose:
        print("Unziping", product_identifier)

    with zipfile.ZipFile(tmp_zip_file) as f:
        f.extractall(safe_file)

    os.remove(tmp_zip_file)

    return safe_file



def download_file_from_google_drive(google_drive_id, destination):
    """
    download files from google drive
    Args:
        google_drive_id (string): for example, given the url:
            https://drive.google.com/uc?id=1YZp2PUR1NYKPlBIVoVRO0Tg1ECDmrnC3&export=download,
            the id is 1YZp2PUR1NYKPlBIVoVRO0Tg1ECDmrnC3
        destination (string): output file


    """
    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value

        return None

    def save_response_content(response, destination):
        CHUNK_SIZE = 32768

        with open(destination, "wb") as f:
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

    URL = "https://docs.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params = { 'id' : google_drive_id}, stream = True)
    token = get_confirm_token(response)

    if token:
        params = { 'id' : google_drive_id, 'confirm' : token}
        response = session.get(URL, params = params, stream = True)

    save_response_content(response, destination)
