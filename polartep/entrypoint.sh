#!/usr/bin/env bash
# args: date
# out: fsc.tif

# Run python code
git pull /root/ai4artic_snow
python /root/ai4artic_snow/main.py $1

