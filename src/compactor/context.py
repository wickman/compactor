import asyncio
import logging
import threading

from .event import DispatchEvent
from .pid import PID
from .process_manager import ProcessManager
from .socket_manager import DEFAULT_SOCKET_MANAGER

from twitter.common.lang import Compatibility

log = logging.getLogger(__name__)


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
               socket_manager_impl=DEFAULT_SOCKET_MANAGER,
               process_manager_impl=ProcessManager,
               loop=None):
    self.delegate = delegate
    self.loop = loop or asyncio.new_event_loop()
    self.socket_manager = socket_manager_impl(self)
    self.process_manager = process_manager_impl(self)
    self.ip, self.port = None, None
    self._initialized = threading.Event()
    super(Context, self).__init__()
    self.daemon = True

  def _initialize_listener(self):
    self.ip, self.port = self.socket_manager.allocate_listener()
    self._initialized.set()

  def run(self):
    self.loop.call_soon(self._initialize_listener)
    self.loop.run_forever()

  def wait_started(self):
    self._initialized.wait()

  def stop(self):
    self.loop.stop()
    self.loop.close()

  def generate_pid(self, id=""):
    if not self._initialized.is_set():
      raise RuntimeError('generate_pid may not be called until the event loop has started.')
    return PID(self.ip, self.port, id)

  def transport(self, message):
    raise NotImplementedError

  def spawn(self, *args, **kw):
    return self.process_manager.spawn(*args, **kw)

  def dispatch(self, pid_or_process, function_or_name, *args):
    if isinstance(pid_or_process, PID):
      pid = pid_or_process
    elif isinstance(pid_or_process, Process):
      pid = pid_or_process.pid
    else:
      raise TypeError('dispatch expects a PID or Process, got %s' % type(pid_or_process))

    if isinstance(function_or_name, Compatibility.string):
      name = function_or_name
    elif callable(function_or_name):
      name = function_or_name.__name__
    else:
      raise TypeError('dispatch expects a function or nae, got %s' % type(function_or_name))

    log.debug('Delivering %s to %s' % (name, pid))
    self.process_manager.deliver(pid, DispatchEvent(name, args))
