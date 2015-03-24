import functools

from .context import Context
from .pid import PID


class Process(object):
  class Error(Exception): pass
  class UnboundProcess(Error): pass

  ROUTE_ATTRIBUTE = '__route__'
  INSTALL_ATTRIBUTE = '__mailbox__'

  @classmethod
  def route(cls, path):
    if not path.startswith('/'):
      raise ValueError('Routes must start with "/"')

    def wrap(fn):
      setattr(fn, cls.ROUTE_ATTRIBUTE, path)
      return fn

    return wrap

  # We'll probably need to make route and install opaque, and just have them delegate to
  # some argument container that can then be introspected by the process implementations.
  @classmethod
  def install(cls, mbox):
    def wrap(fn):
      setattr(fn, cls.INSTALL_ATTRIBUTE, mbox)
      return fn
    return wrap

  def __init__(self, name):
    self.name = name
    self._delegates = {}
    self._http_handlers = dict(self.iter_routes())
    self._message_handlers = dict(self.iter_handlers())
    self._context = None

  def __iter_callables(self):
    # iterate over the methods in a way where we can differentiate methods from descriptors
    for method in type(self).__dict__.values():
      if callable(method):
        # 'method' is the unbound method on the class -- we want to return the bound instancemethod
        yield getattr(self, method.__name__)

  def iter_routes(self):
    for function in self.__iter_callables():
      if hasattr(function, self.ROUTE_ATTRIBUTE):
        yield getattr(function, self.ROUTE_ATTRIBUTE), function

  def iter_handlers(self):
    for function in self.__iter_callables():
      if hasattr(function, self.INSTALL_ATTRIBUTE):
        yield getattr(function, self.INSTALL_ATTRIBUTE), function

  def initialize(self):
    pass

  def _assert_bound(self):
    if not self._context:
      raise self.UnboundProcess('Cannot get pid of unbound process.')

  def bind(self, context):
    if not isinstance(context, Context):
      raise TypeError('Can only bind to a Context, got %s' % type(context))
    self._context = context

  @property
  def pid(self):
    self._assert_bound()
    return PID(self._context.ip, self._context.port, self.name)

  @property
  def context(self):
    self._assert_bound()
    return self._context

  @property
  def route_paths(self):
    return self._http_handlers.keys()

  @property
  def message_names(self):
    return self._message_handlers.keys()

  def delegate(self, name, pid):
    self._delegates[name] = pid

  def handle_message(self, name, from_pid, body):
    if name in self._message_handlers:
      self._message_handlers[name](from_pid, body)
    elif name in self._delegates:
      to = self._delegates[name]
      self._context.transport(to, name, body, from_pid)

  def handle_http(self, route, handler, *args, **kw):
    return self._http_handlers[route](handler, *args, **kw)

  def exited(self, pid):
    pass

  def lost(self, pid):
    pass

  def send(self, to, method, body=None):
    self._assert_bound()
    self._context.send(self.pid, to, method, body)

  def link(self, to):
    self._assert_bound()
    self._context.link(self.pid, to)

  def terminate(self):
    self._assert_bound()
    self._context.terminate(self.pid)


class ProtobufProcess(Process):
  @classmethod
  def install(cls, message_type):
    def wrap(fn):
      @functools.wraps(fn)
      def wrapped_fn(self, from_pid, message_str):
        message = message_type()
        message.MergeFromString(message_str)
        return fn(self, from_pid, message)
      return Process.install(message_type.DESCRIPTOR.full_name)(wrapped_fn)
    return wrap

  def send(self, to, message):
    super(ProtobufProcess, self).send(to, message.DESCRIPTOR.full_name, message.SerializeToString())
