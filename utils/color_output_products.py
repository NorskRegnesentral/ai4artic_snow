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


def sgs_to_color(fsc_map, export):
    """
    Standard coloring for SGS maps
    Args:
        fsc_map: (M x N)  - values 0-100 = fsc %, -1 = cloud, -2 = no data / outside ROI
        export (bool): wheter or not the output is ment export to tiff file or presentation (slightly different color-maps

    Returns:
        RGB image as np.array (M x N x 3)

    """
    assert (len(fsc_map.shape)==2), 'Expected 2D input, got shape {}'.format(fsc_map.shape)

    return _to_color(
        fsc_map,
        _sgs_color_table +  (_common_color_table_export if export else _common_color_table_presentation )
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
_sgs_color_table = [
        ( 0, 1, (0,	0,	255)),
        ( 1, 60, (0,	0,	255)),
        ( 60, 61, (0,	0,	255)),
        ( 61, 62, (0,	0,	180)),
        ( 62, 63, (20,	0,	190)),
        ( 63, 64, (40,	0,	200)),
        ( 64, 65, (60,	0,	210)),
        ( 65, 66, (80,	0,	220)),
        ( 66, 67, (90,	0,	225)),
        ( 67, 68, (100,	0,	230)),
        ( 68, 69, (105,	0,	235)),
        ( 69, 70, (110,	0,	240)),
        ( 70, 71, (115,	0,	245)),
        ( 71, 72, (120,	0,	250)),
        ( 72, 73, (130,	0,	250)),
        ( 73, 74, (140,	0,	250)),
        ( 74, 75, (150,	0,	250)),
        ( 75, 76, (160,	0,	250)),
        ( 76, 77, (170,	0,	250)),
        ( 77, 78, (180,	0,	250)),
        ( 78, 79, (190,	0,	250)),
        ( 79, 80, (200,	0,	250)),
        ( 80, 81, (210,	0,	250)),
        ( 81, 82, (220,	0,	250)),
        ( 82, 83, (230,	0,	250)),
        ( 83, 84, (240,	0,	250)),
        ( 84, 85, (255,	0,	255)),
        ( 85, 86, (250,	0,	230)),
        ( 86, 87, (250,	0,	190)),
        ( 87, 88, (250,	0,	150)),
        ( 88, 89, (240,	0,	110)),
        ( 89, 90, (230,	0,	100)),
        ( 90, 91, (225,	0,	90)),
        ( 91, 92, (220,	0,	80)),
        ( 92, 93, (215,	0,	70)),
        ( 93, 94, (210,	0,	60)),
        ( 94, 95, (205,	0,	50)),
        ( 95, 96, (200,	0,	40)),
        ( 96, 97, (195,	0,	30)),
        ( 97, 98, (190,	0,	20)),
        ( 98, 99, (185,	0,	10)),
        ( 99, 100, (180,0,	0)),
        (100, 101, (255,0,	0))
    ]

_common_color_table_presentation = [
    (-3, -2, (136, 191, 136)), #Ground partly covered with snow (for sgs, ssw)
    (-2, -1, (60, 180, 245)), #No data/outside ROI
    (-1, 0, (128, 128, 128)), # Cloud
]


_common_color_table_export = [
    (-3, -2, (136, 191, 136)), #Ground partly covered with snow (for sgs, ssw)
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

    # if np.sum(np.isnan(r)):
    #     print('Warning, function "_to_color": some pixels are still left un-colored')

    return np.concatenate([r,g,b],-1).astype('uint8')


