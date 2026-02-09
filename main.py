"""
Convert CTF MEG files to MNE-Python raw format.

This app converts CTF MEG .ds folder files to MNE-compatible .fif format using
the mne.io.read_raw_ctf function. It handles temporary file management and 
generates a report with channel information.

Input:
    - ds: Path to CTF .ds folder

Output:
    - out_dir/raw.fif: MNE raw data file
    - out_report/report.html: QC report with channel information
    - product.json: Metadata with channel info
"""

# Copyright (c) 2026 brainlife.io
#
# This app converts CTF MEG files to MNE raw format.
#
# Authors:
# - Guiomar Niso (https://github.com/guiomar)

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'brainlife_utils'))

# Standard imports
import shutil
import mne
import mne_bids

# Import shared utilities
from brainlife_utils import (
    load_config,
    setup_matplotlib_backend,
    ensure_output_dirs,
    create_product_json,
    add_info_to_product,
    add_raw_info_to_product
)

# Set up matplotlib for headless execution
setup_matplotlib_backend()

# Ensure output directories exist
ensure_output_dirs('out_dir', 'out_report')

# Load configuration
config = load_config()

# == LOAD DATA ==
fname = config['ds']

# Create a temporary working copy of the CTF folder
fname_temp = fname[:-6] + 'raw_meg.ds'
if os.path.exists(fname_temp):
    shutil.rmtree(fname_temp)
mne_bids.copyfiles.copyfile_ctf(fname, fname_temp)

try:
    # Read CTF raw data
    raw = mne.io.read_raw_ctf(fname_temp)

    # == CREATE REPORT ==
    report = mne.Report(title='CTF MEG to MNE Conversion Report')
    report.add_raw(raw=raw, title='Raw Data')

    # Add channel information to report
    info_str = str(raw.info)
    report.add_text(info_str, 'Channel Information')

    # Save report
    report.save(os.path.join('out_report', 'report.html'), overwrite=True)

    # == SAVE OUTPUT ==
    raw.save(os.path.join('out_dir', 'raw.fif'), overwrite=True)

    # == CREATE PRODUCT JSON ==
    product_json = create_product_json()
    add_info_to_product(product_json, f"CTF MEG file converted successfully")
    add_raw_info_to_product(product_json, raw)

finally:
    # Clean up temporary file
    if os.path.exists(fname_temp):
        shutil.rmtree(fname_temp)