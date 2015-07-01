from strip import Strip
from hue import HueLight

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
}

LIGHTS = {
    'strip': Strip(dev=SERIAL_DEV),
    'hue': HueLight(bridge_ip='192.168.3.240', light_ids=[1,2,3,4], transition_time=2),
}
