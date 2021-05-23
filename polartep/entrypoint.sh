#!/usr/bin/env bash
# args: date
# out: fsc.tiff

# Run python code
cp scihub_credentials.txt ~/ai4artic_snow/
pip install netCDF4
python ~/ai4artic_snow/main.py $1
