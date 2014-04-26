import asyncio
from collections import defaultdict
import logging
import socket
import threading

from .httpd import HTTPD

from twitter.common.lang import Compatibility
from tornado.netutil import bind_sockets

log = logging.getLogger(__name__)


class Context(threading.Thread):
  _SINGLETON = None
  _LOCK = threading.Lock()

  @classmethod
  def make_socket(cls):
    ip = socket.gethostbyname(socket.gethostname())
    s = bind_sockets(0, address=ip)[0]
    ip, port = s.getsockname()
    return s, ip, port

  @classmethod
  def singleton(cls, delegate="", **kw):
    with cls._LOCK:
      if cls._SINGLETON:
        if cls._SINGLETON.delegate != delegate:
          raise RuntimeError('Attempting to construct different singleton context.')
      else:
        cls._SINGLETON = cls(delegate=delegate, **kw)
    return cls._SINGLETON

  def __init__(self, delegate="", http_server_impl=HTTPD, loop=None):
    self._processes = {}
    self._links = defaultdict(set)
    self.delegate = delegate
    self.loop = loop or asyncio.new_event_loop()
    self.socket, self.ip, self.port = self.make_socket()
    self.http = http_server_impl(self.socket, self.loop)
    super(Context, self).__init__()
    self.daemon = True

  def run(self):
    self.loop.run_forever()

  def stop(self):
    self.loop.stop()
    self.loop.close()

  def spawn(self, process):
    process.bind(self)
    process.initialize()
    self.http.mount_process(process)
    self._processes[process.pid] = process
    return process.pid

  def dispatch(self, pid, method, *args):
    method = getattr(self._processes[pid], method)
    self.loop.call_soon_threadsafe(method, *args)

  def send(self, to, method, body=None):
    pass

  def link(self, pid, to):
    self._links[pid].add(to)

  def terminate(self, pid):
    process = self._processes.pop(pid, None)
    if process:
      self.http.unmount_process(process)
    for link in self._links.pop(pid, []):
      # TODO(wickman) Not sure why libprocess doesn't send termination events
      pass

  def __str__(self):
    return 'Context(%s:%s)' % (self.ip, self.port)
