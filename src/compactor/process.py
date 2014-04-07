class Process(object):
  ROUTE_ATTRIBUTE = '__route__'
  INSTALL_ATTRIBUTE = '__mailbox__'

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

  def __init__(self, name, context=None):
    self._events = []
    self._delegates = {}
    self._message_handlers = {}
    self._http_handlers = {}
    self._context = context or Context.singleton()
    self._pid = self._context.generate_pid(name)

  @property
  def pid(self):
    return self._pid

  def initialize(self):
    for attribute_name in dir(self):
      attribute = getattr(self, attribute_name)
      if not callable(attribute):
        continue
      if hasattr(attribute, self.ROUTE_ATTRIBUTE):
        self._http_handlers[getattr(attribute, self.ROUTE_ATTRIBUTE)] = attribute
      if hasattr(attribute, self.INSTALL_ATTRIBUTE):
        self._message_handlers[getattr(attribute, self.INSTALL_ATTRIBUTE)] = attribute

  def send(self, to, method, body=None):
    return self._context.send(to, method, body)


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
