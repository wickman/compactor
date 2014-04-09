import functools
import threading

from .context import Context
from .process import Process


_ROOT_CONTEXT = None


def initialize(delegate="", **kw):
  global _ROOT_CONTEXT
  _ROOT_CONTEXT = Context.singleton(delegate=delegate, **kw)


def after_init(fn):
  @functools.wraps(fn)
  def wrapper_fn(*args, **kw):
    initialize()
    return fn(*args, **kw)
  return wrapper_fn


@after_init
def spawn(process_cls, *args, **kw):
  """Spawn a process and return its pid."""
  return _ROOT_CONTEXT.spawn(process)


@after_init
def link(process, to):
  return _ROOT_CONTEXT.link(process, to)


@after_init
def send(to, name, data=None):
  """Send data to a remote process at `to` with the name `name`."""
  return _ROOT_CONTEXT.send(to, name, data=data)


route = Process.route
install = Process.install
