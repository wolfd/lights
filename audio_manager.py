"""
    Handles the setting of LED colors
"""

import threading
import subprocess
import os
import decorators
import time

def get_sinks():
    proc = subprocess.Popen(['pacmd', 'list-sinks'], stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    devs = []
    for line in out.split('\n'):
        line = line.strip()
        if line.startswith('name:'):
            devs.append(line[5:].strip()[1:-1].strip())
    return devs

def get_windows(pid):
    env = dict(os.environ)
    env['DISPLAY'] = ':0'
    proc = subprocess.Popen(['xdotool', 'search', '--sync', '--pid', str(pid)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env)
    stdout = proc.communicate()[0]
    lines = stdout.strip().split('\n')[1:]
    return [int(line) for line in lines]

def get_active_window():
    env = dict(os.environ)
    env['DISPLAY'] = ':0'
    proc = subprocess.Popen(['xdotool', 'getactivewindow'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env)
    return int(proc.communicate()[0].strip().split('\n')[-1])

def set_active_window(window):
    env = dict(os.environ)
    env['DISPLAY'] = ':0'
    window = str(window)
    proc = subprocess.Popen(['xdotool',
        'windowactivate', window,
        'windowfocus', window],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env)
    proc.communicate()

def start_visual(window):
    env = dict(os.environ)
    env['DISPLAY'] = ':0'
    window = str(window)
    proc = subprocess.Popen(['xdotool',
        'windowactivate', window,
        'windowfocus', window,
        'key', 'ctrl+n',
        'set_desktop_for_window', window, '1'], env=env)
    proc.wait()

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
            cur_win = get_active_window()
            proc = subprocess.Popen(['/usr/bin/projectM-pulseaudio'], env=env)
            self.proc = proc
            windows = []
            while len(windows) < 3:
                windows = get_windows(proc.pid)
                print windows
                time.sleep(.1)
            window = windows[-1]
            start_visual(window)
            set_active_window(cur_win)
        finally:
            self.lock.release()
