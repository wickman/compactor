import asyncio
import threading

from .pid import PID
from .process_manager import ProcessManager
from .socket_manager import SocketManager


class Context(threading.Thread):
  _SINGLETON = None
  _LOCK = threading.Lock()

  @classmethod
  def singleton(cls, delegate="", **kw):
    with cls._LOCK:
      if cls._SINGLETON:
        if cls._SINGLETON.delegate != delegate:
          raise RuntimeError('Attempting to construct different singleton context.')
      else:
        cls._SINGLETON = cls(delegate=delegate, **kw)
    return cls._SINGLETON

  def __init__(self,
               delegate="",
               socket_manager_impl=SocketManager,
               process_manager_impl=ProcessManager,
               loop=None):
    self.delegate = delegate
    self.loop = loop or asyncio.new_event_loop()
    self.socket_manager = socket_manager_impl(self.loop)
    self.process_manager = process_manager_impl(delegate, self.loop)
    self.socket, self.ip, self.port = None, None, None
    super(Context, self).__init__()
    self.daemon = True

  def _initialize_listner(self):
    self.socket, self.ip, self.port = self.socket_manager.allocate_listener()

  def run(self):
    self.loop.call_soon(self._initialize_listener)
    self.loop.run_forever()

  def generate_pid(self, id=""):
    if self.socket is None:
      raise RuntimeError('generate_pid may not be called until the event loop has started.')
    return PID(id, self.ip, self.port)
