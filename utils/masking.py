import numpy as np


def s3_masking(
    S8_BT_in,
    S9_BT_in,
    S1_reflectance_an,
    S5_reflectance_an,
    S7_BT_in,
    solar_angle=None,
    max_solar_angle=None,
):
    """
        mask s3 images and perform scda2 algorithm for cloud-mask estimation

    Args:
        bt11:
        bt12:
        r550:
        r1600:
        bt37:
        max_solar_angle:

    Returns:
            cloud_map with same shape as input data filled with values: 0, 1, 2
            0 = No data
            1 = Detected clouds
            2 = Detected no clouds
    """
    ## 'BT 10850 nm'
    ## 'BT 12000 nm'
    ## 'reflectance 555 nm (green)'
    ## 'reflectance 1610 nm (SWIR 2)'
    ## 'BT  3740 nm'
    bt11 = S8_BT_in
    bt12 = S9_BT_in
    r550 = S1_reflectance_an
    r1600 = S5_reflectance_an
    bt37 = S7_BT_in

    nl, ns = bt11.shape[:2]
    dt = bt11.dtype

    ndsi = (r550 - r1600) / (r550 + r1600)  ## snowindex

    # Determine where in image there is data
    inside_map = np.zeros((nl, ns), dt)
    inside_map[:] = 0
    inside_map[(r550 >= -1.0) & (r1600 >= -1.0)] = 1

    # Cloud algorithm
    cloud_map_1 = ((r550 > 0.30) & (ndsi / r550 < 0.8) & (bt12 <= 290)) * 1
    cloud_map_2 = (
        (bt11 - bt37 < -13)
        & (r550 > 0.15)
        & (ndsi >= -0.3)
        & (r1600 > 0.1)
        & (bt12 <= 293)
    ) * 1

    thrmax = ((r550 < 0.75) & (bt12 > 265)) * -5.5
    thrmax[((r550 >= 0.75) | (bt12 <= 265))] = -8.0

    s = (r550 > 0.75) * 1.1
    s[(r550 <= 0.75)] = 1.5
    thr1 = 0.5 * bt12 - 133
    thr = (thr1 < thrmax) * thr1 + (thr1 >= thrmax) * thrmax
    cloud_map_3 = (
        (bt11 - bt37 < thr)
        & (ndsi / r550 < s)
        & (-0.02 <= ndsi)
        & (ndsi <= 0.75)
        & (bt12 <= 270)
        & (r550 > 0.18)
    ) * 1
    cloud_map_4 = (bt11 - bt37 < -30) * 1

    # Make cloud map
    cloud_map = np.zeros_like(bt11, dtype="int8")  # Default to no data
    cloud_map[
        ((cloud_map_1 + cloud_map_2 + cloud_map_3 + cloud_map_4) >= 1)
    ] = 1  # 1 is used to indicate cloud
    cloud_map[
        ((cloud_map_1 + cloud_map_2 + cloud_map_3 + cloud_map_4) < 1)
    ] = 2  # 2 is used to indicate non-cloud

    # Mask out pixels with no data
    cloud_map[np.isnan(bt11)] = 0
    cloud_map[np.isnan(bt12)] = 0
    cloud_map[np.isnan(r550)] = 0
    cloud_map[np.isnan(r1600)] = 0
    cloud_map[np.isnan(bt37)] = 0
    cloud_map[inside_map == 0] = 0

    cloud_map[(r550 + r1600) <= 0] = 0  # Outside data

    if solar_angle is not None:
        cloud_map[solar_angle.mask] = 0
        cloud_map[(solar_angle > max_solar_angle)] = 0

    return cloud_map
