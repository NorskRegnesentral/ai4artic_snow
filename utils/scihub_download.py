"""
Module with functions to work with API scihub.
"""
import os
import zipfile
import requests
from sentinelsat import SentinelAPI, geojson_to_wkt, read_geojson
import datetime
import shapely.wkt


DIRNAME = os.path.dirname(os.path.abspath(__file__))

try:
    with open(os.path.join(DIRNAME,'..','scihub_credentials.txt')) as f:
        lines = f.readlines()
        user, password = lines[0:2]
        user = user.strip('\n').strip('\b')
        password = password.strip('\n').strip('\b')
except:
    raise Exception('Could not read login-credentials for scihub.copernicus.eu. These should be stored in "scihub_credentials.txt". See README.md for more instructions.')

api = SentinelAPI(user, password, 'https://scihub.copernicus.eu/dhus')

now = datetime.datetime.now().date()- datetime.timedelta(days=1)

def get_product_identifiers(date):
    date = date.date()
    footprint = geojson_to_wkt(read_geojson(os.path.join(DIRNAME, 'norway_sweden.json')))
    scenes = api.query(footprint, date=(date , date+ datetime.timedelta(days=1)), raw='Sentinel-3')

    selected_scenes = []
    for scene in scenes.values():
        id = scene['identifier']

        #Only S3A SLSTR level 1
        if 'S3A_SL_1_RBT___' not in id:
            continue
        poly1 = shapely.wkt.loads(footprint)
        poly2 = shapely.wkt.loads(scene['footprint'])
        intersection = poly1.intersection(poly2)

        #Require some overlap
        if intersection.area < 10:
            continue
        hour_of_day = int(id.split('_')[7].split('T')[1][:2])

        #Limit to morning passes
        if not( 7 <= hour_of_day <= 11):
            continue
        selected_scenes.append(id)


    return selected_scenes
def download_sentinel_data(  product_identifier, output_location, verbose=1, timeout=10 * 60, debug=False ):
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


    products = api.query( identifier=product_identifier)
    if len(products) != 1:
        raise Exception('Could not find unique product with identifier:', product_identifier)

    result = api.download_all(products, output_location)
    if not len(result[0]) and len(result[1]):
        raise Exception('Product were not available (only from LTA):', product_identifier)

    tmp_zip_file = os.path.join(output_location, product_identifier + '.zip')
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
