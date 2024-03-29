"""
Module with functions to work with API from www.eocloud.eu.
"""
import os
import zipfile
import requests
from sentinelsat import SentinelAPI, geojson_to_wkt, read_geojson
import datetime
import shapely.wkt

from utils.creodias_download import download, query

DIRNAME = os.path.dirname(os.path.abspath(__file__))


def get_product_identifiers(date):
    date = date.date()
    footprint = geojson_to_wkt(read_geojson(os.path.join(DIRNAME, 'norway_sweden.json')))

    scenes = query(
        'Sentinel3',
        start_date=date,
        end_date=date+ datetime.timedelta(days=1),
        geometry=footprint,
    )

    selected_scenes = []
    for scene in scenes.values():
        id = scene['properties']['title']

        #Only S3A SLSTR level 1
        if 'S3A_SL_1_RBT___' not in id:
            continue
        poly1 = shapely.wkt.loads(footprint)
        poly2 = shapely.wkt.loads(geojson_to_wkt(scene))
        intersection = poly1.intersection(poly2)

        #Require some overlap
        if intersection.area/poly1.area < .10:
            continue
        hour_of_day = int(id.split('_')[7].split('T')[1][:2])

        #Limit to morning passes
        if not( 7 <= hour_of_day <= 12):
            continue
        selected_scenes.append(scene)


    return selected_scenes
def download_sentinel_data(  scene, output_location):
    """
    Download and unzip a tile with satelite data.

    Args:
        product_identifier (string): Product identifier
        output_location (string): Location of where to put unzip output data
        verbose (int): Print progress (verbose==1)
        timeout (int): seconds to timeout wget. On timeout download is restarted up to 10 times
        debug (bool): run on main thread if set to True (timeout is ignored)

    Returns:
        string: Path to SEN3-folder
    """
    global api

    product_identifier = scene['properties']['title'].replace('.SEN3','')
    tmp_zip_file = os.path.join(output_location, product_identifier + '.zip')

    download(scene['id'], tmp_zip_file, show_progress=True)
    # if not len(result[0]) and len(result[1]):
    #     raise Exception('Product were not available (only from LTA):', product_identifier)

    safe_file = os.path.join(output_location, product_identifier + ".SAFE")

    with zipfile.ZipFile(tmp_zip_file) as f:
        f.extractall(safe_file)

    os.remove(tmp_zip_file)

    return os.path.join(safe_file, product_identifier+'.SEN3')


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
