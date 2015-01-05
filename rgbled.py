
import serial
import threading
import traceback
import time


class Strip(object):
    def __init__(self, dev):
        self.dev = dev
        self.conn = None
        self.lock = threading.Lock()
        self.connect()

    def connect(self):
        self.lock.acquire()
        try:
            self.conn = serial.Serial(self.dev, baudrate=115200)
            self.conn.write(chr(255) + chr(0) + chr(0) + chr(0))
            self.conn.flush()
        finally:
            self.lock.release()

    def set_color(self, *args):
        while True:
            try:
                self.conn.write(chr(255))
                self.conn.write(''.join(chr(c if c < 255 else 254) for c in args))
                self.conn.flush()
                return
            except Exception:
                print 'Error setting color:\n%s' % traceback.format_exc()
                try:
                    self.connect()
                except Exception:
                    print 'Error reconnecting: %s' % traceback.format_exc()
                    time.sleep(1)

    def close(self):
        self.lock.acquire()
        try:
            self.conn.close()
        finally:
            self.lock.release()

    def __del__(self):
        self.conn.close()
