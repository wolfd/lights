import logging
import time
from phue import Bridge
import colorsys
from colorpy import colormodels

LOG = logging.getLogger('ledcontrol')

class HueLight(object):
    def __init__(self, bridge_ip=None, light_ids=None, transition_time=2):
        super(HueLight, self).__init__()
        self.b = None
        self.light_ids = light_ids
        self.bridge_ip = bridge_ip
        self.transition_time = transition_time

    def connect(self):
        self.b = Bridge(self.bridge_ip)
        self.b.set_light(self.light_ids, {
            'on': True,
            'transitiontime': self.transition_time,
        })

    def set_color(self, r, g, b):
        try:
            rgb = colormodels.irgb_color(r, g, b)
            xyz = colormodels.xyz_from_rgb(rgb)
            xyz = colormodels.xyz_normalize(xyz)
            command = {
                'xy': [xyz[0], xyz[1]],
            }
            self.b.set_light(self.light_ids, command)
            time.sleep(0.30)

        except Exception:
            LOG.exception('Couldn\'t send command to Hue Bridge')
