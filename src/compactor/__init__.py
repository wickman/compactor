import functools

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
  @functools.wraps(fn)
  def wrapper_fn(*args, **kw):
    initialize()
    return fn(*args, **kw)
  return wrapper_fn


@after_init
def spawn(process):
  """Spawn a process and return its pid."""
  return _ROOT_CONTEXT.spawn(process)


@after_init
def link(process, to):
  return _ROOT_CONTEXT.link(process, to)


@after_init
def send(to, name, data=None):
  """Send data to a remote process at `to` with the name `name`."""
  return _ROOT_CONTEXT.send(to, name, data=data)


del after_init


route = Process.route
install = Process.install


__all__ = (
  'initialize',
  'install',
  'join',
  'link',
  'route',
  'task',
  'send',
  'spawn',
)
