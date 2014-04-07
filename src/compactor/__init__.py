import functools
import threading

from .context import Context


_ROOT_CONTEXT = None


def initialize(delegate=""):
  global _ROOT_CONTEXT
  _ROOT_CONTEXT = Context.singleton(delegate)


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
def dispatch(process_or_pid, function_or_name, *args):
  """Dispatch a function/name with arguments to a process/pid.

  Returns a Future of the return value.
  """
  return _ROOT_CONTEXT.dispatch(process_or_pid, function_or_name, *args)


@after_init
def delay(amount, process_or_pid, function_or_name, *args):
  """Dispatch a function/name with arguments to a process/pid after a delay.

  Returns a Future of the return value.
  """
  return _ROOT_CONTEXT.delay(amount, process_or_pid, function_or_name, *args)


@after_init
def send(to, name, data=None):
  """Send data to a remote process at `to` with the name `name`."""
  return _ROOT_CONTEXT.send(to, name, data=data)
