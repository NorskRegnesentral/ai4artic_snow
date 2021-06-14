#!/usr/bin/env bash
# args: date
# out: fsc.tif

# Run python code
cp scihub_credentials.txt /root/ai4artic_snow
cp creodias_credentials.txt /root/ai4artic_snow
git pull /root/ai4artic_snow
python /root/ai4artic_snow/main.py $1
cp /root/ai4artic_snow/fsc /workdir/fsc.tif

