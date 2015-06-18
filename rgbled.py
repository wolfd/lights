
import serial
import threading
import traceback
import time
import logging
import threading
import Queue

LOG = logging.getLogger('ledcontrol')


LAST_STRIP = None

def add_hook(f):
    if LAST_STRIP:
        LAST_STRIP.add_hook(f)

def remove_hook(f):
    if LAST_STRIP:
        LAST_STRIP.remove_hook(f)



class Strip(object):
    def __init__(self, dev):
        self.dev = dev
        self.conn = None
        self.lock = threading.Lock()
        self.connect()
        self.hooks = {}
        global LAST_STRIP
        LAST_STRIP = self

    def add_hook(self, callback):
        q = Queue.Queue(30)
        self.hooks[callback] = q
        def writer():
            while callback in self.hooks:
                color = q.get()
                try:
                    callback(*color)
                except Exception:
                    print traceback.format_exc()
                    del self.hooks[callback]
                    break
        t = threading.Thread(target=writer)
        t.daemon = True
        t.start()

    def remove_hook(self, callback):
        if callback in self.hooks:
            del self.hooks[callback]

    def connect(self):
        self.lock.acquire()
        try:
            self.conn = serial.Serial(self.dev, baudrate=115200)
            self.conn.write(chr(255) + chr(0) + chr(0) + chr(0))
            self.conn.flush()
        finally:
            self.lock.release()

    def write_color_to_queues(self, *args):
        for q in self.hooks.values():
            try:
                q.put_nowait(tuple(args))
            except Exception:
                pass

    def set_color(self, *args):
        while True:
            try:
                self.conn.write(chr(255))
                self.conn.write(''.join(chr(c if c < 255 else 254) for c in args))
                self.conn.flush()
                self.write_color_to_queues(*args)
                return
            except Exception:
                LOG.warning('Error setting color:\n%s', traceback.format_exc())
                try:
                    self.connect()
                except Exception:
                    LOG.warning('Error reconnecting: %s', traceback.format_exc())
                    time.sleep(1)

    def close(self):
        self.lock.acquire()
        try:
            self.conn.close()
        finally:
            self.lock.release()

    def __del__(self):
        self.conn.close()
