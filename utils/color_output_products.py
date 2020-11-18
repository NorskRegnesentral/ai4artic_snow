import numpy as np

def fsc_to_color(fsc_map, export):
    """
    Standard coloring for FSC maps
    Args:
        fsc_map: (M x N)  - values 0-100 = fsc %, -1 = cloud, -2 = no data / outside ROI
        export (bool): wheter or not the output is ment export to tiff file or presentation (slightly different color-maps

    Returns:
        RGB image as np.array (M x N x 3)

    """
    assert (len(fsc_map.shape)==2), 'Expected 2D input, got shape {}'.format(fsc_map.shape)

    return _to_color(
        fsc_map,
        _fsc_color_table +  (_common_color_table_export if export else _common_color_table_presentation )
    )


# Color table format:
#   Each entry has:
#   (min_value - inclusive, max_value - exclusive, color-triplet)

_fsc_color_table = [
        (0, 10, (30, 125, 30)),
        (10, 20, (53, 138, 53)),
        (20, 30, (75, 151, 75)),
        (30, 40, (98, 164, 98)),
        (40, 50, (120, 177, 120)),
        (50, 60, (143, 190, 143)),
        (60, 70, (165, 203, 165)),
        (70, 80, (188, 216, 188)),
        (80, 90, (210, 229, 210)),
        (90, 100, (233, 242, 233)),
        (100, 101, (254, 254, 254)),
    ]

_common_color_table_presentation = [
    (-2, -1, (60, 180, 245)), #No data/outside ROI
    (-1, 0, (128, 128, 128)), # Cloud
]


_common_color_table_export = [
    (-2, -1, (255, 255, 255)), #No data/outside ROI
    (-1, 0, (128, 128, 128)), # Cloud
]

def _to_color(map, color_table):
    """
    Funciton to colorize based on 2D map with values and a colortable

    """

    r = np.zeros(list(map.shape) + [1], dtype='uint8')*np.nan
    g = np.zeros(list(map.shape) + [1], dtype='uint8')*np.nan
    b = np.zeros(list(map.shape) + [1], dtype='uint8')*np.nan

    for from_, to_, color in color_table:
        inds = np.where( np.bitwise_and(from_ <= map, map < to_))

        r[inds] = color[0]
        g[inds] = color[1]
        b[inds] = color[2]

    if np.sum(np.isnan(r)):
        print('Warning, function "_to_color": some pixels are still left un-colored')

    return np.concatenate([r,g,b],-1).astype('uint8')


