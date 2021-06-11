#!/usr/bin/env bash
# args: date
# out: fsc.tiff

# Run python code
cp scihub_credentials.txt /root/ai4artic_snow
cp creodias_credentials.txt /root/ai4artic_snow
cd /root/ai4artic_snow
git pull
python /root/ai4artic_snow/main.py $1

