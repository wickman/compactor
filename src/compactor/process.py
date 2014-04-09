import threading

from .context import Context
from .event import (
    DispatchEvent,
    ExitedEvent,
    HttpEvent,
    MessageEvent,
    TerminatedEvent,
)


class Process(object):
  ROUTE_ATTRIBUTE = '__route__'
  INSTALL_ATTRIBUTE = '__mailbox__'
  
  class Error(Exception): pass
  class UnboundProcess(Error): pass

  @classmethod
  def route(cls, path):
    def wrap(fn):
      setattr(fn, cls.ROUTE_ATTRIBUTE, path)
      return fn
    return wrap

  @classmethod
  def install(cls, mbox):
    def wrap(fn):
      setattr(fn, cls.INSTALL_ATTRIBUTE, mbox)
      return fn
    return wrap

  def __init__(self, name):
    self.name = name
    self._delegates = {}
    self._message_handlers = {}
    self._http_handlers = {}
    self._context = None

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
    return PID(self.name, self._context.ip, self._context.port)

  def initialize(self):
    for attribute_name in dir(self):
      attribute = getattr(self, attribute_name)
      if not callable(attribute):
        continue
      if hasattr(attribute, self.ROUTE_ATTRIBUTE):
        self._http_handlers[getattr(attribute, self.ROUTE_ATTRIBUTE)] = attribute
      if hasattr(attribute, self.INSTALL_ATTRIBUTE):
        self._message_handlers[getattr(attribute, self.INSTALL_ATTRIBUTE)] = attribute

  def delegate(self, name, pid):
    self._delegates[name] = pid

  def __handle_message(self, event):
    if event.message.name in self._message_handlers:
      self._message_handlers[event.message.name](
          self.event.message.from_,
          self.event.message.body)
    elif event.message.name in self._delegates:
      delegated_message = Message(*self.event.message)
      delegated_message.to = self._delegates[event.message.name]
      self._context.transport(delegated_message)

  def __handle_dispatch(self, event):
    function = getattr(self, event.name, None)
    if function is None:
      raise RuntimeError('Unknown function %s on %s' % (event.name, self))
    function(*event.args)

  def __handle_http(self, event):
    pass

  def __handle_exit(self, event):
    pass

  def __handle_terminate(self, event):
    pass

  def __handle_one(self, event):
    if isinstance(event, MessageEvent):
      self.__handle_message(event)
    elif isinstance(event, DispatchEvent):
      self.__handle_dispatch(event)
    elif isinstance(event, HttpEvent):
      self.__handle_http(event)
    elif isinstance(event, ExitedEvent):
      self.__handle_exit(event)
    elif isinstance(event, TerminatedEvent):
      self.__handle_terminate(event)
    else:
      raise ValueError('Unknown event: %s' % type(event))

  def exited(self, pid):
    pass
  
  def lost(self, pid):
    pass

  def serve(self, event):
    self._assert_bound()
    self.__handle_one(event)

  def send(self, to, method, body=None):
    self._assert_bound()
    self._context.send(to, method, body)

  def link(self, to):
    self._assert_bound()
    self._context.link(self.pid, to)

  def terminate(self):
    self._assert_bound()
    self._context.terminate(self.pid)


"""

class ProtobufProcess(Process):
  def send(self, to, message):
    message_name = message.__class__.__name__
    body = message.SerializeToString()
    return super(ProtobufProcess, self).send(to, message_name, body)


class QueueProcess(Process):
  def __init__(self, **kw):
    ...
    super(QueueProcess, self).__init__('queue', **kw)

  @install('enqueue')
  def enqueue(self, body):
    pass

  @install('dequeue')
  def dequeue(self):
    pass


class CompactorFuture(asyncio.Future):
  def on_any()
  def then(self, function, *args, **kw):
    # create a new future that gets linked
    # so you can do
    # compactor.dispatch(queue.dequeue).then(
    #     compactor.dispatch, queue.enqueue)


import compactor
from compactor.process import Process

compactor.initialize('executor')
queue = compactor.spawn(QueueProcess)
compactor.dispatch(queue.enqueue, 42)
compactor.dispatch(queue.dequeue).then(print)
compactor.send(master_pid, 'enqueue', 'pooping')
compactor.send(master_pid, 'ping')


# Implement first:
#   dispatch
#   spawn

# then:
#   install
#   local send

# Then:
#   route
#   remote send


class ProtobufProcess

class ThriftProcess

class JSONProcess

"""
