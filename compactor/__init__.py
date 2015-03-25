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
  _ROOT_CONTEXT.join()


def after_init(fn):
  @wraps(fn)
  def wrapper_fn(*args, **kw):
    initialize()
    return fn(*args, **kw)
  return wrapper_fn


@after_init
def spawn(process):
  """Spawn a process and return its pid."""
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


del Context
del Process
del after_init
del wraps
