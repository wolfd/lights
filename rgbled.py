
import serial
import threading

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
        finally:
            self.lock.release()

    def set_color(self, *args):
        self.conn.write(chr(255))
        self.conn.write(''.join(chr(c if c < 255 else 254) for c in args))
        self.conn.flush()

    def close(self):
        self.lock.acquire()
        try:
            self.conn.close()
        finally:
            self.lock.release()

    def __del__(self):
        self.conn.close()
