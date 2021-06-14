#!/usr/bin/env bash
# args: date
# out: fsc.tif

# Run python code
git -C /root/ai4artic_snow pull
python /root/ai4artic_snow/main.py $1

