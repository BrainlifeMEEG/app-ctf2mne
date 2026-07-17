"""
Convert CTF MEG files to MNE-Python raw format.

This app converts CTF MEG .ds folder files to MNE-compatible .fif format using
the mne.io.read_raw_ctf function. It handles temporary file management, detects
events, identifies and marks bad/flat channels, and generates a QC report with
channel information and a power spectral density (PSD) plot.

Input:
    - ds: Path to CTF .ds folder
    - eog: Comma-separated list of EOG channel names (optional)
    - ecg: Comma-separated list of ECG channel names (optional)
    - misc: Comma-separated list of miscellaneous channel names (optional)
    - bads: Comma-separated list of bad channel names to mark (optional)
    - rm_flat: Whether to automatically detect and mark flat channels (default: True)

Output:
    - out_dir/raw.fif: MNE raw data file
    - out_report/report.html: QC report with channel information
    - out_figs/psd.png: Power spectral density plot
    - product.json: Metadata with channel info, bad channels, and QC messages
"""

# Copyright (c) 2026 brainlife.io
#
# This app converts CTF MEG files to MNE raw format.
#
# Authors:
# - Guiomar Niso (https://github.com/guiomar)
# - Maximilien Chaumon (https://github.com/dnacombo)
# - Anandapadmanabhan Unnikrishnan (https://github.com/obVdo)

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'brainlife_utils'))

# Standard imports
import shutil
import mne
import numpy as np
import mne_bids
import matplotlib.pyplot as plt

# Import shared utilities
from brainlife_utils import (
    load_config,
    setup_matplotlib_backend,
    ensure_output_dirs,
    create_product_json,
    add_info_to_product,
    add_raw_info_to_product,
    add_image_to_product
)

# Set up matplotlib for headless execution
setup_matplotlib_backend()

# Ensure output directories exist
ensure_output_dirs('out_dir', 'out_figs', 'out_report')

# Load configuration
config = load_config()

# == LOAD DATA ==
fname = config['ds']

# Create a temporary working copy of the CTF folder
fname_temp = fname[:-6] + 'raw_meg.ds'
if os.path.exists(fname_temp):
    shutil.rmtree(fname_temp)
mne_bids.copyfiles.copyfile_ctf(fname, fname_temp)


eog = config.get('eog', None)
if eog is not None:
    eog = [ch.strip() for ch in eog.split(',')]
else:
    eog = None
ecg = config.get('ecg', None)
if ecg is not None:
    ecg = [ch.strip() for ch in ecg.split(',')]
else:
    ecg = None
misc = config.get('misc', None)
if misc is not None:
    misc = [ch.strip() for ch in misc.split(',')]
else:
    misc = None

try:
    # Read CTF raw data
    raw = mne.io.read_raw_ctf(fname_temp)
    
        
   # read events from raw
    events = mne.find_events(raw, shortest_event=1)
    event_id = {f"Event{event}": event for event in np.unique(events[:, 2])}
    
    already_bad = raw.info['bads'].copy()
    if already_bad:
        print(f"Channels already marked as bad in the CTF file: {', '.join(already_bad)}")

    if config.get('rm_flat', True):
        # remove any channel that is strictly flat
        idx = np.std(raw.get_data(), axis=1) == 0
        flat_channels = [raw.info['ch_names'][i] for i in np.where(idx)[0]]
        if flat_channels:
            raw.info['bads'].extend(flat_channels)
            raw.info['bads'] = list(set(raw.info['bads']))  # Remove duplicates
            print(f"Flat channels marked as bads: {', '.join(flat_channels)}")
    else:
        flat_channels = []
    
    # == MARK BAD CHANNELS ==
    bads_raw = config.get('bads', '')
    if bads_raw and bads_raw != 'None':
        bads = [ch.strip() for ch in bads_raw.split(',')]
        # Filter to only include channels that exist in the data
        bads = [ch for ch in bads if ch in raw.ch_names]
        if bads:
            raw.info['bads'].extend(bads)
            raw.info['bads'] = list(set(raw.info['bads']))  # Remove duplicates
            print(f"Newly marked as bads: {', '.join(bads)}")
    else:
        bads = []
    
    # == CREATE REPORT ==
    report = mne.Report(title='CTF MEG to MNE Conversion Report')
    report.add_raw(raw=raw, title='Raw Data')
    
    # Add channel information to report
    channel_info_html = '<p><b>Channels in this EGI file:</b></p>' + ', '.join(raw.ch_names)
    report.add_html(title='Channels', html=channel_info_html)

    # Save report
    report.save(os.path.join('out_report', 'report.html'), overwrite=True, verbose=False)
    
    raw.save(os.path.join('out_dir', 'raw.fif'), overwrite=True)
    
    # == CREATE PSD PLOT ==
    fig = raw.compute_psd().plot(exclude='bads', show=False)
    fig.savefig(os.path.join('out_figs', 'psd.png'), dpi=100, bbox_inches='tight')
    plt.close(fig)

    # == CREATE PRODUCT JSON ==
    product_items = []

    # Add structured raw info messages
    add_raw_info_to_product(product_items, raw)

    # Add bad channels information if any
    if raw.info['bads']:
        already_bad_msg = f"Channels already marked as bad in the CTF file: {', '.join(already_bad)}" if already_bad else "No channels were marked as bad in the original CTF file."
        add_info_to_product(product_items, already_bad_msg, 'warning' if already_bad else 'info')
        if config.get('rm_flat', True):
            flat_msg = f"Flat channels marked: {', '.join(flat_channels)}" if flat_channels else "No flat channels detected."
            add_info_to_product(product_items, flat_msg, 'warning' if flat_channels else 'info')
        bads_msg = f"Bad channels marked: {', '.join(bads)}" if bads else "No additional bad channels marked from config."
        add_info_to_product(product_items, bads_msg, 'info')
        final_bads_msg = f"Total bad channels marked: {', '.join(raw.info['bads'])}"
        add_info_to_product(product_items, final_bads_msg, 'success')

    # Add channel positions if available
    positions = raw._get_channel_positions()
    if positions is not None and np.any(~np.isnan(positions)):
        channel_positions_msg = "Channel positions:\n" + "\n".join(
            [f"{ch_name}: {pos.tolist()}" for ch_name, pos in zip(raw.ch_names, positions)]
        )
        add_info_to_product(product_items, channel_positions_msg)
    else:
        add_info_to_product(product_items, f"Channels (no positions available): {', '.join(raw.ch_names)}")

    add_info_to_product(product_items, "Imported CTF .raw file and converted to MNE format successfully.", msg_type='success')

    # Add PSD plot if it exists
    psd_image_path = os.path.join('out_figs', 'psd.png')
    if os.path.exists(psd_image_path):
        add_image_to_product(product_items, name='Power Spectral Density (PSD)', filepath=psd_image_path)

    create_product_json(product_items)
        
finally:
    # Clean up temporary file
    if os.path.exists(fname_temp):
        shutil.rmtree(fname_temp)