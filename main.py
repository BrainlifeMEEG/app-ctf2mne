# Copyright (c) 2020 brainlife.io
#
# This file is a MNE python-based brainlife.io App
#
# Author: Guiomar Niso
# Indiana University

# set up environment
import os
import json
import mne
import mne_bids
import shutil

# Current path
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

# Populate mne_config.py file with brainlife config.json
with open(__location__+'/config.json') as config_json:
    config = json.load(config_json)


fname = config['ds']


# Rename ds folder so internal files match
# FIND A TEMPORAL FOLDER (ask soichi)
# mne_bids.copyfiles.copyfile_ctf(fname, 'meg.ds')
fname1 = fname[:-6]+'raw_meg.ds'
if os.path.exists(fname1):
  shutil.rmtree(fname1)
mne_bids.copyfiles.copyfile_ctf(fname, fname1)


# COPY THE METADATA CHANNELS.TSV, COORDSYSTEM, ETC ==============================


raw = mne.io.read_raw_ctf(fname1)

# save mne/raw
raw.save(os.path.join('out_dir','raw.fif'))

# Remove temporal file
if os.path.exists(fname1):
  shutil.rmtree(fname1)

# create a product.json file to show info in the process output
info = raw.info
dict_json_product = {'brainlife': []}

info = str(info)
dict_json_product['brainlife'].append({'type': 'info', 'msg': info})

with open('product.json', 'w') as outfile:
    json.dump(dict_json_product, outfile)