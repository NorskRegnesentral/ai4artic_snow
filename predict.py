import numpy as np
import torch
import os

from utils.data_download import download_file_from_google_drive
from utils.masking import s3_masking
from utils.rasterio_utils import to_tiff
from utils.tiled_prediction import tiled_prediction
from utils.unet import UNet

#Download trained model
_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model.pt')
if not os.path.isfile(_model_path):
    download_file_from_google_drive('19b41UQB0ylUIQEeH5I_7UAeyjNl5f31H', _model_path)

#Make tmp-folder
_tmp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')
if not os.path.isdir(_tmp_path):
    os.makedirs(_tmp_path)


def predict(
    S1_reflectance_an,
    S2_reflectance_an,
    S3_reflectance_an,
    S4_reflectance_an,
    S5_reflectance_an,
    S6_reflectance_an,
    S7_BT_in,
    S8_BT_in,
    S9_BT_in,
    name = None,
    transform= None
):
    """
    Function to apply trained model to data
    Args:
        S1_reflectance_an (np.array): S3 data band
        S2_reflectance_an (np.array): S3 data band
        S3_reflectance_an (np.array): S3 data band
        S4_reflectance_an (np.array): S3 data band
        S5_reflectance_an (np.array): S3 data band
        S6_reflectance_an (np.array): S3 data band
        S7_BT_in (np.array): S3 data band
        S8_BT_in (np.array): S3 data band
        S9_BT_in (np.array): S3 data band
        name (None, str): name of product (used for tmp-file generation)
        transform (rasterio._warp.Affine): geo transform for product

    Returns:
        (rbg image, fsc image) - if name is not None, then output is paths to the respective images. Otherwise it is the np.arrays
    """
    name = name.split('/')[-1]
    data_cube = [
        S1_reflectance_an,
        S2_reflectance_an,
        S3_reflectance_an,
        S4_reflectance_an,
        S5_reflectance_an,
        S6_reflectance_an,
        S7_BT_in,
        S8_BT_in,
        S9_BT_in,
    ]
    data_cube = [d[:, :, None] for d in data_cube]
    data_cube = np.concatenate(data_cube,-1)
    data_cube[np.isnan(data_cube)] = 0

    model = UNet(n_classes=1, in_channels=9, depth=4, use_bn=True, partial_conv=True)
    model.load_state_dict( torch.load( _model_path ) )
    model.cuda()
    model.eval()
    fsc = tiled_prediction(data_cube, model, [512, 512], [128, 128]).squeeze()
    fsc = np.clip(fsc, 0, 100)

    mask = s3_masking(
        S8_BT_in,
        S9_BT_in,
        S1_reflectance_an,
        S5_reflectance_an,
        S7_BT_in,
    )
    fsc[mask == 1] = -1 #Clouds
    fsc[mask == 0] = -2 #No data

    #Make an OK pseudo RGB render
    rgb = np.clip(np.sqrt(data_cube[:, :, [4, 2, 0]]), 0, 1)*100
    rgb = rgb * (mask[:, :, None] == 2).astype("float") - 2 * ( mask[:, :, None] != 2 ).astype( "float" )  # No data == -2
    rgb[np.concatenate([mask[:, :, None] == 1] * 3, -1)] = 100  # Clouds are white

    # Write to file
    if name is not None:
        fp_fsc = os.path.join(_tmp_path, name + '_fsc.tif')
        to_tiff(fp_fsc, fsc.astype("int8"), transform, no_data_val=-2)

        fp_rgb = os.path.join(_tmp_path, name + '_rgb.tif')
        to_tiff(fp_rgb,rgb.astype("int8"), transform, no_data_val=-2)

        return fp_fsc, fp_rgb
    #Or return np.arrays
    else:
        return fsc, rgb

