"""
    Module for managing and running LED patterns
"""

import cherrypy
import multiprocessing
import multiprocessing.queues
import os
import sys
import threading
import time
import traceback

import decorators
import settings

class PatternRunner(object):
    """
        Manages the execution of an LED pattern
    """
    def __init__(self, pattern, set_color):
        self.pattern = pattern
        self.set_color = set_color
        self.err_info = None
        self.proc = None
        self.thread = None
        self.started = None
        self.ended = None
        self.lock = threading.Lock()

    def stop(self):
        """
            Stops a pattern and waits for it to finish executing, then turns
            off the LEDs.
        """
        self.lock.acquire()
        try:
            if self.proc and self.proc.is_alive():
                os.kill(self.proc.pid, 9)
                self.thread.join()
                self.ended = time.time()
        finally:
            self.lock.release()

    def __run_in_proc(self, col_queue, ret_queue, pattern):
        """
            Runs the pattern code inside of the process
        """
        cherrypy.engine.signal_handler.unsubscribe()
        cherrypy.server.unsubscribe()
        
        locs = locals()
        globs = globals()
        globs['set_color'] = lambda r, g, b: col_queue.put((r, g, b))
        try:
            exec pattern in globs, locs
        except Exception:
            ret_queue.put(traceback.format_exc())
            sys.exit(2)

    def __run_in_thread(self, pattern):
        """
            This method is what runs inside a pattern thread. It handles the
            actual execution of the pattern and handles any exceptions thrown.
        """
        col_queue = multiprocessing.queues.SimpleQueue()
        ret_queue = multiprocessing.queues.SimpleQueue()
        args = (col_queue, ret_queue, pattern)
        proc = multiprocessing.Process(target=self.__run_in_proc, args=args)
        self.proc = proc
        proc.start()
        # Put set_color in a local variable to reduce lookups
        set_color = self.set_color
        while proc.is_alive():
            if col_queue.empty():
                time.sleep(.001)
            else:
                col_tuple = col_queue.get()
                set_color(*col_tuple)
        if proc.exitcode == 2:
            self.err_info = ret_queue.get()
        elif proc.exitcode <= 0:
            # Process was either killed or exited cleanly
            pass
        else:
            self.err_info = 'Unknown error'

    def start(self,):
        """
            Starts the execution of a pattern
        """
        pattern = self.pattern
        thread = threading.Thread(target=self.__run_in_thread, args=(pattern,))
        thread.daemon = True
        self.thread = thread
        self.lock.acquire()
        try:
            self.thread.start()
            self.started = time.time()
        finally:
            self.lock.release()

    def get_status(self):
        """
            Gets the current status information about a pattern if it is
            runnig.
        """
        self.lock.acquire()
        try:
            if self.started is None:
                duration = None
            elif self.ended is None:
                duration = time.time() - self.started
            else:
                duration = self.ended - self.started
            return {
                'running': (self.proc and self.proc.is_alive()),
                'err_info': self.err_info,
                'duration': duration
            }
        finally:
            self.lock.release()

class Manager(object):
    """
        Manages LED color patterns defined as Python scripts.
    """
    def __init__(self, server):
        self.server = server
        self.current_name = None
        self.current = None
        self.lock = threading.RLock()

    def __get_pattern(self, name):
        """
            Reads a saved pattern script from disk and returns it as a string.
            
        """
        path = os.path.join(settings.PATTERN_DIR, name + '.pattern')
        with open(path, 'r') as fobj:
            return fobj.read()

    def release_strip(self):
        """
            Called by the controller to tell the manager to release the strip
            gracefully.
        """
        self.lock.acquire()
        try:
            if self.current:
                self.current.stop()
        finally:
            self.lock.release()

    @decorators.expose(output='text')
    def get_status(self):
        """
            Gets the status of the current pattern
        """
        output = []
        output.append('Current: %s\n' % self.current_name)
        if self.current:
            status = self.current.get_status()
            output.append('Running: %s\n' % status['running'])
            output.append('Duration: %s\n' % status['duration'])
            if status['err_info']:
                output.append('Error:\n%s\n' % status['err_info'])
        return ''.join(output)

    @decorators.expose(method='post', output=None)
    def save_pattern(self, name, text):
        self.lock.acquire()
        try:
            path = os.path.join(settings.PATTERN_DIR, name+'.pattern')
            with open(path, 'w') as fobj:
                fobj.write(text)
        finally:
            self.lock.release()

    @decorators.expose()
    def list_patterns(self):
        """
            Returns a list of available pattern names.
        """
        self.lock.acquire()
        try:
            return [name[:-8] for name in os.listdir(settings.PATTERN_DIR) if
                    name.endswith('.pattern')]
        finally:
            self.lock.release()

    @decorators.expose(output='text')
    def get_pattern(self, name):
        """
            Loads a pattern file.
            
            Arguments:
                name - The name of the pattern

            Returns:
                The string contents of the pattern
        """
        self.lock.acquire()
        try:
            return self.__get_pattern(name)
        finally:
            self.lock.release()

    @decorators.expose(output=None)
    def run_pattern(self, name):
        """
            Runs a saved pattern against the lights. This API call returns
            nearly immediately and the pattern remains running in the server
            until the pattern completes or it is stopped.
            
            Arguments:
                name - The name of the pattern
        """
        self.lock.acquire()
        try:
            pattern = self.__get_pattern(name)
            strip = self.server.get_strip()
            self.current_name = name
            self.current = PatternRunner(pattern, strip.set_color)
            self.current.start()
        finally:
            self.lock.release()

