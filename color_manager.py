"""
    Handles the setting of LED colors
"""

import threading
import decorators

class Manager(object):
    """
        Sets all lights to solid colors.
    """
    def __init__(self, server):
        self.server = server
        self.lock = threading.RLock()
        
    def release_dispatcher(self):
        """
            Releases the dispatcher
        """
        self.lock.acquire()
        self.lock.release()
        
    @decorators.expose(output=None)
    def set_color_hex(self, hexrgb):
        """
            Because Josh thinks in webdev.
        """
        self.set_color(*[int(hexrgb[i*2:i*2+2], 16) for i in range(3)])        
        
    @decorators.expose(output=None)
    def set_color(self, red, green, blue):
        """
            Sets all the lights to an RGB color.
            
            Arguments:
                red - (int) from 0-254
                green - (int) from 0-254
                blue - (int) from 0-254
        """
        self.lock.acquire()
        try:
            self.server.get_dispatcher().set_color(int(red), int(green), int(blue))
        finally:
            self.lock.release()
