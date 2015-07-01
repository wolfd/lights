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
import tempfile
import stat
import logging
from subprocess import Popen, PIPE

import decorators
import settings

LOG = logging.getLogger('ledcontrol')

def git(*args):
    git_dir = os.path.join(settings.PATTERN_DIR, '.git')
    cmd = ['git', '--git-dir', git_dir]
    cmd.extend(args)
    proc = Popen(cmd, cwd=settings.PATTERN_DIR, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise Exception(stdout + stderr)
    return stdout


class ScriptRunner(object):
    def __init__(self, pattern, set_color):
        self.pattern = pattern
        self.set_color = set_color
        self.proc = None
        self.log_lines = []
        self.t = None
        
    @property
    def is_running(self):
        try:
            return self.proc.poll() is None
        except Exception:
            return False
        
    def get_status(self):
        return {
            'running': self.is_running,
            'duration': 1,
            'err_info': ''.join(self.log_lines)
        }
        
    def start(self):
        temp = tempfile.NamedTemporaryFile().name
        with open(temp, 'w') as fobj:
            fobj.write(self.pattern)
        os.chmod(temp, stat.S_IEXEC ^ stat.S_IREAD)
        set_color = self.set_color
        proc = Popen(['stdbuf', '-o', 'L', temp], cwd=settings.PATTERN_DIR, stdout=PIPE)
        self.proc = proc
        def watcher():
            while proc.poll() is None:
                line = proc.stdout.readline()
                if line.startswith('color:'):
                    color_str = line.partition(':')[2]
                    color = [int(x.strip()) for x in color_str.split(',')]
                    set_color(*color)
                else:
                    self.log_lines.append(line)
        t = threading.Thread(target=watcher)
        t.daemon = True
        t.start()
        self.t = t
        
    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait()
            except Exception:
                LOG.warning('stop failed: %s', traceback.format_exc())


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
        finally:
            self.lock.release()

    def __run_in_proc(self, col_queue, ret_queue, pattern):
        """
            Runs the pattern code inside of the process
        """
        cherrypy.engine.signal_handler.unsubscribe()
        cherrypy.server.unsubscribe()

        locs = locals().copy()
        globs = globals().copy()

        def script_set_color(r, g, b, name=None):
            col_queue.put((r, g, b, name))

        globs['set_color'] = script_set_color
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
                set_color(*col_tuple[:-1], name=col_tuple[-1])
        self.ended = time.time()
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

    def release_dispatcher(self):
        """
            Called by the controller to tell the manager to release the
            dispatcher gracefully.
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
            try:
                git('status')
            except Exception:
                git('init')
            #git('reset')
            #git('add', path)
            #git('commit', '-m', 'updated pattern "%s"' % name)
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
            dispatcher = self.server.get_dispatcher()
            self.current_name = name
            if pattern.partition('\n')[0].startswith('#!'):
                self.current = ScriptRunner(pattern, dispatcher.set_color)
            else:
                self.current = PatternRunner(pattern, dispatcher.set_color)
            self.current.start()
        finally:
            self.lock.release()

