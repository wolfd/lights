import threading
import traceback
import logging
import Queue
import settings

from hue import HueLight
from strip import Strip

LOG = logging.getLogger('ledcontrol')

class Dispatcher(object):
    """
    Dispatches color changes to lights
    """
    def __init__(self):
        super(Dispatcher, self).__init__()
        self.hooks = {}
        for name, light in settings.LIGHTS.iteritems():
            if hasattr(light, 'connect'):
                light.connect()
            self.add_hook(name, light.set_color)

    def add_hook(self, name, callback, queue_length=5):
        q = Queue.Queue(queue_length)
        self.hooks[callback] = {'name': name, 'queue': q}
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

    def set_color(self, *args, **kwargs):
        fix = lambda x: min(255, max(0, int(x)))
        args = [fix(x) for x in args]
        for hook in self.hooks.values():
            name = kwargs.get('name')
            q = hook['queue']
            if name == None or name == hook['name']:
                try:
                    q.put_nowait(tuple(args))
                except Exception:
                    pass
