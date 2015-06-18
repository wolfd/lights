#!/usr/bin/python2

"""
    Server for controlling LEDs
"""

# built-in modules
import inspect
import json
import os
import threading
import logging
from subprocess import Popen, PIPE

# external modules
import cherrypy
from ws4py.websocket import WebSocket
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool

# project modules
import rgbled
import settings

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
WWW_DIR = os.path.join(SERVER_DIR, 'www')

LOG = logging.getLogger('ledcontrol')


def mimetype(mimeval):
    """
        Decorator factory for CherryPy server methods which sets a mimetype
    """
    def decorate(func):
        """
            Decorator for setting CherryPy mimes
        """
        def wrapper(*args, **kwargs):
            """
                Wrapper function for setting mimes
            """
            cherrypy.response.headers['Content-Type'] = mimeval
            return func(*args, **kwargs)
        return wrapper
    return decorate

def json_dump(obj):
    """
        Returns a pretty-printed JSON string of obj
    """
    return json.dumps(obj, indent=4, sort_keys=True, separators=(',', ': '))

def handle_ouput(out_type, data):
    """
        Handles the output
    """
    if out_type == 'json':
        return 'application/json', json_dump(data)
    elif out_type is None:
        return 'text/plain', ''
    else:
        return 'text/plain', data

def get_documentation(obj):
    """
        Gets documentation of an object
    """
    return getattr(obj, '__doc__', None) or 'No documentation.'

def min_indent(text):
    """
        Finds the minimum indentation in the given text
    """
    lines = text.split('\n')
    mincount = None
    for line in lines:
        if line.strip():
            count = 0
            for char in line:
                if char == ' ':
                     count += 1
                else:
                    break
            if mincount is None or count < mincount:
                mincount = count
    return mincount

def reindent(text, baseindent):
    """
        Reindents text
    """
    mindent = min_indent(text)
    if mindent is None or mindent == baseindent:
        return text
    lines = text.split('\n')
    if mindent > baseindent:
        newlines = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                newlines.append(line[mindent - baseindent:])
            else:
                newlines.append('')
        return '\n'.join(newlines)
    else:
        needed = (baseindent - mindent) * ' '
        newlines = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                newlines.append(needed + line)
            else:
                newlines.append('')
        return '\n'.join(newlines)

class ManagerDispatcher(object):
    """
        Dispatches requests to managers
    """
    def __init__(self, server, manager_name, manager):
        self.server = server
        self.manager_name = manager_name
        self.manager = manager

    def get_exposed(self):
        """
            Gets a dict containing information about exposed methods
        """
        manager = self.manager
        props = dir(manager)
        exposed = {}
        for prop in props:
            method = getattr(manager, prop)
            if callable(method) and hasattr(method, 'info'):
                info = method.info.copy()
                info['doc'] = get_documentation(method)
                aspec = inspect.getargspec(method)
                args = list(aspec.args)[1:]
                info['args'] = args
                defaults = list(aspec.defaults or [])
                defaults = dict(zip(args[-1*len(defaults):], defaults))
                info['defaults'] = defaults                
                exposed[prop] = info
        return exposed

    @cherrypy.expose
    def index(self, fmt='text'):
        data = {
            'name': self.manager_name,
            'doc': get_documentation(self.manager),
            'method_info': self.get_exposed()
        }
        if fmt == 'json':
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json_dump(data)
        else:
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            parts = [
                '%s manager\n' % self.manager_name,
                reindent(data['doc'], 4).strip('\n'),
                '\n\nMethods:\n'
            ]
            names = sorted(data['method_info'].keys())
            for name in names:
                info = data['method_info'][name]
                parts.append('    %s\n' % name)
                doc = reindent(info['doc'], 8).strip('\n')  + '\n\n'
                parts.append(doc)
                if not doc.endswith('\n'):
                    parts.append('\n')
            return ''.join(parts)

    def __getattr__(self, name):
        if hasattr(self.manager, name):
            method = getattr(self.manager, name)
            if callable(method) and hasattr(method, 'info'):
                def wrapped(*args, **kwargs):
                    info = method.info
                    output = method(*args, **kwargs)
                    mime, output = handle_ouput(info['output'], output)
                    cherrypy.response.headers['Content-Type'] = mime
                    return output
                wrapped.exposed = True
                return wrapped
        raise AttributeError('Manager "%s" has no method "%s"' % (
                              self.manager_name, name))

class LedControlServer(object):
    """
        Server class for CherryPy
    """
    def __init__(self):
        self.lock = threading.RLock()
        self.strip = rgbled.Strip(settings.SERIAL_DEV)
        self.managers = {}
        self.dispatchers = {}
        for name, module in settings.MANAGERS.iteritems():
            manager = module.Manager(self)
            self.managers[name] = manager
            self.dispatchers[name] = ManagerDispatcher(self, name, manager)

    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("/lights/catalog.htm", 302)
        
    @cherrypy.expose
    def log(self):
        proc = Popen(['tail', '-n', '500', os.path.join(SERVER_DIR, 'app.log')], stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            raise Exception(stderr)
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return stdout

    @cherrypy.expose
    def ws(self):
        handler = cherrypy.request.ws_handler

    def get_strip(self):
        """
            Releases the strip from all managers
        """
        self.lock.acquire()
        try:
            for manager in self.managers.itervalues():
                manager.release_strip()
            return self.strip
        finally:
            self.lock.release()

    def __getattr__(self, name):
        if name in self.managers:
            return self.dispatchers[name]
        else:
            raise AttributeError('No dispatcher named "%s"' % name)

class LedWebSocket(WebSocket):
    def opened(self):
        f = lambda *args: self.send_rgb(*args)
        self.conn = f
        rgbled.add_hook(f)

    def received_message(self, message):
        print message

    def send_rgb(self, r, g, b):
        self.send("%s,%s,%s" % (r, g, b), False)

    def close(self, code, reason):
        f = self.conn
        try:
            rgbled.remove_hook(f)
        except Exception:
            pass


if __name__ == '__main__':
    cp_logger = logging.getLogger('cherrypy')
    cp_logger.addHandler(logging.FileHandler('./cherrpy.log'))
    other_logger = logging.getLogger('ledcontrol')
    other_logger.addHandler(logging.FileHandler('./app.log'))

    cherrypy.config.update({
        'engine.autoreload.on': False,
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8080,
        'tools.proxy.on': True,
        'tools.proxy.remote': "X-Forwarded-For",
        'tools.proxy.base': 'http://hackhouse.io',
    })
    conf = {
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': WWW_DIR,
        },
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': LedWebSocket
        },
    }

    # WebSocket setup
    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()

    cherrypy.quickstart(root=LedControlServer(), script_name='/lights', config=conf)


