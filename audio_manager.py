"""
    Handles the setting of LED colors
"""

import threading
import subprocess
import os
import decorators

def get_sinks():
    proc = subprocess.Popen(['pacmd', 'list-sinks'], stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    devs = []
    for line in out.split('\n'):
        line = line.strip()
        if line.startswith('name:'):
            devs.append(line[5:].strip()[1:-1].strip())
    return devs

class Manager(object):
    """
        Sets strips to solid colors.
    """
    def __init__(self, server):
        self.server = server
        self.lock = threading.RLock()
        self.proc = None
        self.strip = None

    def release_strip(self):
        """
            Releases the strip
        """
        self.lock.acquire()
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
            self.strip.connect()
            self.strip = None
        self.lock.release()

    @decorators.expose(output='json')
    def get_sinks(self):
        return get_sinks()

    @decorators.expose(output=None)
    def start_visualizer(self):
        """
            Sets the strip to an RGB color.

            Arguments:
                red - (int) from 0-254
                green - (int) from 0-254
                blue - (int) from 0-254
        """
        self.lock.acquire()
        try:
            strip = self.server.get_strip()
            strip.close()
            self.strip = strip
            env = dict(os.environ)
            env['DISPLAY'] = ':0'
            proc = subprocess.Popen(['/usr/bin/projectM-pulseaudio'], env=env)
            self.proc = proc
        finally:
            self.lock.release()
