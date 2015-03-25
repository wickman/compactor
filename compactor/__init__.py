from functools import wraps

from .context import Context
from .process import Process


_ROOT_CONTEXT = None


def initialize(delegate="", **kw):
  global _ROOT_CONTEXT
  _ROOT_CONTEXT = Context.singleton(delegate=delegate, **kw)
  if not _ROOT_CONTEXT.is_alive():
    _ROOT_CONTEXT.start()


def join():
  """Join against the global context -- blocking until the context has been stopped."""
  _ROOT_CONTEXT.join()


def after_init(fn):
  @wraps(fn)
  def wrapper_fn(*args, **kw):
    initialize()
    return fn(*args, **kw)
  return wrapper_fn


@after_init
def spawn(process):
  """Spawn a process on the global context and return its pid.

  :param process: The process to bind to the global context.
  :type process: :class:`Process`
  :returns pid: The pid of the spawned process.
  :rtype: :class:`PID`
  """
  return _ROOT_CONTEXT.spawn(process)


route = Process.route
install = Process.install


__all__ = (
  'initialize',
  'install',
  'join',
  'route',
  'spawn',
)


del after_init
