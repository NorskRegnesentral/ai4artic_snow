from utils.color_output_products import fsc_to_color
import matplotlib
matplotlib.use('Agg') #for headless servers
import matplotlib.pyplot as plt
import numpy as np
import os

def output_plot( path, rgb_merge, fsc_merge, name):
    rgb_merge = rgb_merge.astype('float')
    rgb_merge[rgb_merge == -2] = np.nan
    fsc_merge = fsc_to_color(fsc_merge.squeeze(), export=False)

    plt.figure(figsize=[24, 12])
    ax = plt.subplot(1, 2, 1)
    plt.imshow(rgb_merge.squeeze()/100, interpolation='nearest')
    plt.title('Pseudo RGB ' + name)
    plt.subplot(1, 2, 2, sharex=ax, sharey=ax)
    plt.imshow(fsc_merge.squeeze(), interpolation='nearest')
    plt.title('FSC')
    plt.tight_layout()
    plt.savefig(os.path.join(path,name + '.png'))
    plt.show()
