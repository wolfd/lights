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
    '1': HueLight(bridge_ip='192.168.3.240', light_ids=1, transition_time=2),
    '2': HueLight(bridge_ip='192.168.3.240', light_ids=2, transition_time=2),
    '3': HueLight(bridge_ip='192.168.3.240', light_ids=3, transition_time=2),
    '4': HueLight(bridge_ip='192.168.3.240', light_ids=4, transition_time=2),
    'hue-left': HueLight(bridge_ip='192.168.3.240', light_ids=[1,4], transition_time=2),
    'hue-right': HueLight(bridge_ip='192.168.3.240', light_ids=[2,3], transition_time=2),
}
