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
    """A decorator to indicate that a method should be a routable HTTP endpoint.

    .. code-block:: python

        from compactor.process import Process

        class WebProcess(Process):
          @Process.route('/hello/world')
          def hello_world(self, handler):
            return handler.write('<html><title>hello world</title></html>')

    The handler passed to the method is a tornado RequestHandler.

    WARNING: This interface is alpha and may change in the future if or when
    we remove tornado as a compactor dependency.

    :param path: The endpoint to route to this method.
    :type path: ``str``
    """

    if not path.startswith('/'):
      raise ValueError('Routes must start with "/"')

    def wrap(fn):
      setattr(fn, cls.ROUTE_ATTRIBUTE, path)
      return fn

    return wrap

  # TODO(wickman) Make mbox optional, defaulting to function.__name__.
  # TODO(wickman) Make INSTALL_ATTRIBUTE a defaultdict(list) so that we can
  # route multiple endpoints to a single method.
  @classmethod
  def install(cls, mbox):
    """A decorator to indicate a remotely callable method on a process.

    .. code-block:: python

        from compactor.process import Process

        class PingProcess(Process):
          @Process.install('ping')
          def ping(self, from_pid, body):
            # do something

    The installed method should take ``from_pid`` and ``body`` parameters.
    ``from_pid`` is the process calling the method.  ``body`` is a ``bytes``
    stream that was delivered with the message, possibly empty.

    :param mbox: Incoming messages to this "mailbox" will be dispatched to this method.
    :type mbox: ``str``
    """
    def wrap(fn):
      setattr(fn, cls.INSTALL_ATTRIBUTE, mbox)
      return fn
    return wrap

  def __init__(self, name):
    """Create a process with a given name.

    The process must still be bound to a context before it can send messages
    or link to other processes.

    :param name: The name of this process.
    :type name: ``str``
    """

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
        try:
          yield getattr(self, method.__name__)
        except AttributeError:
          # This is possible for __name_mangled_attributes.
          continue

  def iter_routes(self):
    for function in self.__iter_callables():
      if hasattr(function, self.ROUTE_ATTRIBUTE):
        yield getattr(function, self.ROUTE_ATTRIBUTE), function

  def iter_handlers(self):
    for function in self.__iter_callables():
      if hasattr(function, self.INSTALL_ATTRIBUTE):
        yield getattr(function, self.INSTALL_ATTRIBUTE), function

  def _assert_bound(self):
    if not self._context:
      raise self.UnboundProcess('Cannot get pid of unbound process.')

  def bind(self, context):
    if not isinstance(context, Context):
      raise TypeError('Can only bind to a Context, got %s' % type(context))
    self._context = context

  @property
  def pid(self):
    """The pid of this process.

    :raises: Will raise a ``Process.UnboundProcess`` exception if the
             process is not bound to a context.
    """
    self._assert_bound()
    return PID(self._context.ip, self._context.port, self.name)

  @property
  def context(self):
    """The context that this process is bound to.

    :raises: Will raise a ``Process.UnboundProcess`` exception if the
             process is not bound to a context.
    """
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

  def initialize(self):
    """Called when this process is spawned.

    Once this is called, it means a process is now routable. Subclasses
    should implement this to initialize state or possibly initiate
    connections to remote processes.
    """

  def exited(self, pid):
    """Called when a linked process terminates or its connection is severed.

    :param pid: The pid of the linked process.
    :type pid: :class:`PID`
    """

  def send(self, to, method, body=None):
    """Send a message to another process.

    Sending messages is done asynchronously and is not guaranteed to succeed.

    Returns immediately.

    :param to: The pid of the process to send a message.
    :type to: :class:`PID`
    :param method: The method/mailbox name of the remote method.
    :type method: ``str``
    :keyword body: The optional content to send with the message.
    :type body: ``bytes`` or None
    :raises: Will raise a ``Process.UnboundProcess`` exception if the
             process is not bound to a context.
    :return: Nothing
    """
    self._assert_bound()
    self._context.send(self.pid, to, method, body)

  def link(self, to):
    """Link to another process.

    The ``link`` operation is not guaranteed to succeed.  If it does, when
    the other process terminates, the ``exited`` method will be called with
    its pid.

    Returns immediately.

    :param to: The pid of the process to send a message.
    :type to: :class:`PID`
    :raises: Will raise a ``Process.UnboundProcess`` exception if the
             process is not bound to a context.
    :return: Nothing
    """
    self._assert_bound()
    self._context.link(self.pid, to)

  def terminate(self):
    """Terminate this process.

    This unbinds it from the context to which it is bound.

    :raises: Will raise a ``Process.UnboundProcess`` exception if the
             process is not bound to a context.
    """
    self._assert_bound()
    self._context.terminate(self.pid)


class ProtobufProcess(Process):
  @classmethod
  def install(cls, message_type):
    """A decorator to indicate a remotely callable method on a process using protocol buffers.

    .. code-block:: python

        from compactor.process import ProtobufProcess
        from messages_pb2 import RequestMessage, ResponseMessage

        class PingProcess(ProtobufProcess):
          @ProtobufProcess.install(RequestMessage)
          def ping(self, from_pid, message):
            # do something with message, a RequestMessage
            response = ResponseMessage(...)
            # send a protocol buffer which will get serialized on the wire.
            self.send(from_pid, response)

    The installed method should take ``from_pid`` and ``message`` parameters.
    ``from_pid`` is the process calling the method.  ``message`` is a protocol
    buffer of the installed type.

    :param message_type: Incoming messages to this message_type will be dispatched to this method.
    :type message_type: A generated protocol buffer stub
    """
    def wrap(fn):
      @functools.wraps(fn)
      def wrapped_fn(self, from_pid, message_str):
        message = message_type()
        message.MergeFromString(message_str)
        return fn(self, from_pid, message)
      return Process.install(message_type.DESCRIPTOR.full_name)(wrapped_fn)
    return wrap

  def send(self, to, message):
    """Send a message to another process.

    Same as ``Process.send`` except that ``message`` is a protocol buffer.

    Returns immediately.

    :param to: The pid of the process to send a message.
    :type to: :class:`PID`
    :param message: The message to send
    :type method: A protocol buffer instance.
    :raises: Will raise a ``Process.UnboundProcess`` exception if the
             process is not bound to a context.
    :return: Nothing
    """
    super(ProtobufProcess, self).send(to, message.DESCRIPTOR.full_name, message.SerializeToString())
