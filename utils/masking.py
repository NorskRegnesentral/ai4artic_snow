import numpy as np


def s3_masking(
    S8_BT_in,
    S9_BT_in,
    S1_reflectance_an,
    S5_reflectance_an,
    S7_BT_in,
):
    """
        Perform scda2 algorithm for cloud-mask estimation and detect no-data pixels

    Args:
        bt11:
        bt12:
        r550:
        r1600:
        bt37:

    Returns:
            cloud_map with same shape as input data filled with values: 0, 1, 2
            0 = No data
            1 = Detected clouds
            2 = Detected no clouds
    """
    bt11 = S8_BT_in
    bt12 = S9_BT_in
    r550 = S1_reflectance_an
    r1600 = S5_reflectance_an
    bt37 = S7_BT_in

    cloud_mask = _scda2(r550, r1600, bt37, bt11, bt12)

    mask = np.zeros_like(cloud_mask)
    mask[cloud_mask] = 1
    mask[np.bitwise_not(cloud_mask)] = 2

    mask[(r550 + r1600) <= 0] = 0  # No data

    return mask



def _normalized_difference_index(b1, b2):
    return (b1-b2) / (b1+b2)


def _scda2(r550, r1600, bt37, bt11, bt12):
    ndsi = _normalized_difference_index(r550, r1600)

    thrmax = np.where((r550 < 0.75) & (bt12 > 265), -5.5, -8.0)
    thr1 = 0.5*bt12 - 133
    thr = np.minimum(thr1, thrmax)

    s = np.where(r550 > 0.75, 1.1, 1.5)

    cloud1 = ((r550 > 0.3)
              & (ndsi/r550 < 0.8)
              & (bt12 < 290))
    cloud2 = ((bt11-bt37 < -13)
              & (r550 > 0.15)
              & (ndsi >= -0.3)
              & (r1600 > 0.1)
              & (bt12 <= 293))
    cloud3 = ((bt11-bt37 < thr)
              & (ndsi/r550 < s)
              & (-0.02 <= ndsi) & (ndsi <= 0.75)
              & (bt12 <= 270)
              & (r550 > 0.18))
    cloud4 = bt11-bt37 < -30

    cloud = (cloud1 | cloud2 | cloud3 | cloud4)

    cloud = cloud

    return cloud