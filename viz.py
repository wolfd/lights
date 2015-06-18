#!/usr/bin/env python2

import sys
import numpy as np
from subprocess import Popen, PIPE

SAMPLE_RATE = 44100

NUM_BANDS = 12
FOURIERS_PER_SECOND = 24
FOURIER_SPREAD = 1.0/FOURIERS_PER_SECOND
FOURIER_WIDTH = FOURIER_SPREAD
FOURIER_WIDTH_INDEX = FOURIER_WIDTH * float(SAMPLE_RATE)
FOURIER_SPACING = round(FOURIER_SPREAD * float(SAMPLE_RATE))
SAMPLE_SIZE = FOURIER_WIDTH_INDEX
FREQ = SAMPLE_RATE / SAMPLE_SIZE * np.arange(SAMPLE_SIZE)

BANDWIDTH = float(SAMPLE_RATE)/SAMPLE_SIZE

# Run `pacmd list-sinks` to find this info
PULSE_DEVICE = 'alsa_output.pci-0000_05_00.1.hdmi-stereo-extra1.monitor'
# NOTE(ali): move to config variable (or remove lol)

def read_samples():
    chunk_sz = int(SAMPLE_SIZE - 1) * 2
    #cmd = ['parec', '--format=s16le', '--device', PULSE_DEVICE]
    cmd = [
        'sox', '-q', '--buffer', '250', '-D', '--rate', str(SAMPLE_RATE),
        '-d', '--rate', str(SAMPLE_RATE), '-L', '-t', 's16', '-'
    ]
    proc = Popen(cmd, stdout=PIPE)
    while proc.poll() is None:
        raw_data = proc.stdout.read(chunk_sz)
        data = np.frombuffer(raw_data, dtype=np.int16)
        yield data
    if proc.returncode != 0:
        raise Exception('wtf even')

def freq_to_index(f):
    if f < BANDWIDTH/2:
        return 0
    if f > (SAMPLE_RATE / 2) - (BANDWIDTH / 2):
        return SAMPLE_SIZE - 1
    fraction = float(f) / float(SAMPLE_RATE)
    return int(round(SAMPLE_SIZE * fraction))

def average_fft_bands(fft_array):
    fft_averages = []
    for band in range(NUM_BANDS):
        if band == 0:
            low_freq = 0
        else:
            low_freq = (SAMPLE_RATE/2) / (2 ** (NUM_BANDS - band))
        hi_freq = (SAMPLE_RATE/2) / (2 ** (NUM_BANDS - 1 - band))
        low_bound = freq_to_index(low_freq)
        hi_bound = freq_to_index(hi_freq)

        avg = sum(fft_array[low_bound:hi_bound]) / (hi_bound - low_bound + 1)
        fft_averages.append(avg)
    return fft_averages

def avg(l):
    return sum(l)/len(l)


def viz_data():
    for sample in read_samples():
        fft_data = abs(np.fft.fft(sample))
        fft_data  *= ((2**.5)/SAMPLE_SIZE)
        yield average_fft_bands(fft_data)


