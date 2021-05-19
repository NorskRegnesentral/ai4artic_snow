import os

import numpy as np

from predict import predict
from preprocess import  convert_sen3
from utils.data_download import download_sentinel_data
from utils.output_plot import output_plot
from utils.rasterio_utils import merge_tiff_files



if __name__ == "__main__":

    # Scenes to process
    scenes =['S3A_SL_1_RBT____20200326T100236_20200326T100536_20200327T152414_0179_056_236_1980_LN2_O_NT_004.SEN3',
             'S3A_SL_1_RBT____20200326T114035_20200326T114335_20200327T173937_0179_056_237_1800_LN2_O_NT_004.SEN3',
             'S3A_SL_1_RBT____20200326T113735_20200326T114035_20200327T173840_0179_056_237_1620_LN2_O_NT_004.SEN3',
             'S3A_SL_1_RBT____20200326T082136_20200326T082436_20200327T132011_0179_056_235_1980_LN2_O_NT_004.SEN3',
             'S3A_SL_1_RBT____20200326T095936_20200326T100236_20200327T152311_0179_056_236_1800_LN2_O_NT_004.SEN3',
             'S3A_SL_1_RBT____20200326T081836_20200326T082136_20200327T131915_0179_056_235_1800_LN2_O_NT_004.SEN3',
             'S3A_SL_1_RBT____20200326T095636_20200326T095936_20200327T152208_0179_056_236_1620_LN2_O_NT_004.SEN3']

    work_dir = os.path.dirname(os.path.abspath(__file__)) #Both tmp-files and output files go here

    epsg = 32633

    rgb_imgs = []
    fsc_imgs = []

    for s3_scene_identifier in scenes:

        # Download scene
        safe_file = '/nr/samba/jo/pro/AI4Artic/usr/andersuw/ai4artic_snow/S3A_SL_1_RBT____20200521T091019_20200521T091319_20200522T132040_0179_058_264_1980_LN2_O_NT_004.SEN3'#download_sentinel_data(s3_scene_identifier, work_dir)

        # Open SEN3 file, convert from swath mode, convert to reflectance
        data_channels, transform = convert_sen3(safe_file, epsg)

        # Predict
        fsc_tiff, rgb_tiff = predict(
            *data_channels,
            s3_scene_identifier,
            transform
        )

        rgb_imgs.append(rgb_tiff)
        fsc_imgs.append(fsc_tiff)

    # Export tiff
    rgb_merge = merge_tiff_files(rgb_imgs, 'rgb.tif', no_data_val=-2)
    fsc_merge = merge_tiff_files(fsc_imgs, 'fsc.tif', no_data_val=-2)

    # Plot images
    output_plot('.', rgb_merge, fsc_merge, 'fsc')
