# AI4Artic - snow   
#### Estimation of snow-parameters from sentinel-3 data using deep learning

The goal of [the AI4Artic project](https://www.esa.int/Applications/Observing_the_Earth/Using_artificial_intelligence_to_automate_sea-ice_charting)
were to develop AI/deep learning - based estimation of snow and ice parameters from  Sentinel data. The project was 
funded by ESA. This repository contains code for the snow-part of the project. The code for the ice-part can be found 
[here](https://github.com/damaha/asip-v2).


The deep learning model is based on the [UNet architecture](https://arxiv.org/abs/1505.04597). The input data is Sentinel-3 data from the SLSTR sensor. The model outputs the following snow-parameters as geotiff files:
- Fractional snow cover (FSC) with values; FSC:0-100, cloud:-1, no data:-2
- Snow grain size (SGS) with (uncalibrated) values; SGS:60-100, cloud:-1, no data:-2
- Snow surface wetness (SSW) classes with values; Dry, cold snow: 0, Dry, moderate cold snow: 1, Dry, warming snow: 2, Moist snow: 3, Moist, warming snow: 4, Wet snow: 4, cloud:-1, no data:-2

### Setup
Make sure you are running the code on a computer with python 3 and GDAL installed. Type the following commands in the terminal to setup the repository and python environment:
    
    git clone git@github.com:NorskRegnesentral/ai4artic_snow.git
    cd ai4artic_snow
    python -m virtualenv env
    source env/bin/activate
    pip install -r REQUIREMENTS.txt
    wget PUT_MODEL_URL_HERE

#### Save scihub-credentials to a text file to enable data-download
Create an account at scihub.copernicus.eu (if you dont already have one). Create a new file at the root of this repository named
```
scihub_credentials.txt
```
Make two lines in the text file, the first with your username and the second with your password.

### Usage
```
python main.py YYYYMMDD
```
Where YYYYMMDD is a date for which you desire snow products for. If omitted, the date for yesterday will be used.

- main.py: A script to run the entire snow-pipeline
 
    1. user specify which date to process
    2. data-downloading
    3. preprocessing (conversion to reflectance) 
    4. deep learning prediction 
    5. mosaicing and export 

        
### Contact
For questions, contact [Anders U. Waldeland](https://www.nr.no/user-info?query=andersuw) at 
anders@nr.no