import os
import sys
import datetime
import traceback

from predict import predict
from preprocess import  convert_sen3
from utils.data_download import download_sentinel_data, get_product_identifiers
from utils.output_plot import output_plot
from utils.rasterio_utils import merge_tiff_files


if __name__ == "__main__":

    # Parse selected date
    debug_flag = False
    if len(sys.argv) == 2:
        if sys.argv[1] == 'DEBUG':
            date = datetime.datetime.now() - datetime.timedelta(days=1)  # Use yesterday as default
            debug_flag = True
            with open('fsc.tif','w') as f:
                f.write('ehy')
            exit(0)
        else:
            try:
                date = datetime.datetime.strptime(sys.argv[1], "%Y%m%d")
            except ValueError as e:
                print("Could not parse date")
                raise e
    else:
        date = datetime.datetime.now() - datetime.timedelta(days=1) #Use yesterday as default

    # Find scenes to process
    scenes = get_product_identifiers(date)

    if debug_flag:
        scenes = scenes[0:1] #Make it a bit faster by only running one scene

    if len(scenes) == 0:
        print('Could not find any S3 scenes for {}. Please select a more recent date')
    print('Processing {} scenes from {}'.format(len(scenes), date))

    work_dir = os.path.dirname(os.path.abspath(__file__)) #Both tmp-files and output files go here

    rgb_imgs = []
    fsc_imgs = []

    for i,scene in enumerate(scenes):
        s3_scene_identifier = scene['properties']['title']
        print('{}/{} {}'.format(i,len(scenes), s3_scene_identifier))
        try:

            # Download scene
            sen3_folder = download_sentinel_data(scene, work_dir)

            # Open SEN3 file, convert from swath mode, convert to reflectance
            data_channels, transform = convert_sen3(sen3_folder)

            # Predict
            fsc_tiff, rgb_tiff = predict(
                *data_channels,
                s3_scene_identifier,
                transform
            )

            rgb_imgs.append(rgb_tiff)
            fsc_imgs.append(fsc_tiff)
        except:
            print('Failed {}/{} {}'.format(i, len(scenes), s3_scene_identifier))
            traceback.print_exc()

    # Export tiff
    rgb_merge = merge_tiff_files(rgb_imgs, 'rgb.tif', no_data_val=-2)
    fsc_merge = merge_tiff_files(fsc_imgs, 'fsc.tif', no_data_val=-2)

    # Plot images
    output_plot('.', rgb_merge, fsc_merge, 'fsc')


