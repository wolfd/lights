"""
    This module contains settings to be used by the other modules
"""

# The path to the serial device to use
SERIAL_DEV = '/dev/arduino'

# The path to the directory where patterns should be stored
PATTERN_DIR = '/home/hackhouse/ledcontrol/patterns/'

MANAGERS = {
    'pattern': __import__('pattern_manager'),
    'color': __import__('color_manager'),
    'audio': __import__('audio_manager')
}
