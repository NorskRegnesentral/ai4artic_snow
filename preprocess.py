

def preprocess(sen3_file, epsg):
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

    # Todo: Implement algorithm to convert reflectance here.



    # Hack to main.py work on NR servers while this funciton is developed
    import os
    from  tqdm import tqdm
    import numpy as np
    from netCDF4._netCDF4 import Dataset

    with open('/lokal-uten-backup-1tb/ai4artic_path.txt') as f:
        ARCHIVE_S3_DATA_PATH = f.readline().strip('\n')
    files =[]
    date = "S3A_SL_1_RBT____20200326T100236_20200326T100536_20200327T152414_0179_056_236_1980_LN2_O_NT_004.SEN3".split('_')[7][:8]

    folders = os.listdir(ARCHIVE_S3_DATA_PATH)
    for dirpath in folders:
        if date in dirpath:
            if 'reflectance' in os.listdir(os.path.join(ARCHIVE_S3_DATA_PATH, dirpath)):
                for file in os.listdir(os.path.join(ARCHIVE_S3_DATA_PATH, dirpath, 'reflectance')):
                    path_to_file = os.path.join(ARCHIVE_S3_DATA_PATH, dirpath, 'reflectance', file)
                    if Dataset(path_to_file).variables['source_meta'].filename == sen3_file:
                        files.append(path_to_file)
                        break
    ds = Dataset(files[0])

    # Find region with data
    s3_transform = [
        ds.variables['x'][1] - ds.variables['x'][0],
        0,
        float(ds.variables['x'][0]),
        0,
        ds.variables['y'][1] - ds.variables['y'][0],
        float(ds.variables['y'][0]),
    ]

    data_cube = []
    bands = ['S1_reflectance_an', 'S2_reflectance_an', 'S3_reflectance_an', 'S4_reflectance_an', 'S5_reflectance_an',
             'S6_reflectance_an', 'S7_BT_in', 'S8_BT_in', 'S9_BT_in']

    for band in bands:
        data = ds.variables[band][:].data
        data[data == ds.variables[band]._FillValue] = np.nan
        data_cube.append(data)

    return data_cube, s3_transform
