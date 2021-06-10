#!/usr/bin/env bash
# args: date
# out: fsc.tiff

# Run python code
cp scihub_credentials.txt ~/ai4artic_snow/
cp creodias_credentials.txt ~/ai4artic_snow/
cd ~/ai4artic_snow/
git pull
python ~/ai4artic_snow/main.py $1
