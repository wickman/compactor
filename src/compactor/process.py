import threading

from .context import Context
from .pid import PID


class Process(object):
  ROUTE_ATTRIBUTE = '__route__'
  INSTALL_ATTRIBUTE = '__mailbox__'

  class Error(Exception): pass
  class UnboundProcess(Error): pass

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
    self._http_handlers = {}
    self._message_handlers = {}
    self._context = None

  def initialize(self):
    self._http_handlers.update(self.iter_routes())
    self._message_handlers.update(self.iter_handlers())

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
  def route_paths(self):
    return self._http_handlers.keys()

  @property
  def message_names(self):
    return self._message_handlers.keys()

  def iter_callables(self):
    for attribute_name in dir(self):
      attribute = getattr(self, attribute_name)
      if not callable(attribute):
        continue
      yield attribute

  def iter_routes(self):
    for function in self.iter_callables():
      if hasattr(function, self.ROUTE_ATTRIBUTE):
        yield getattr(function, self.ROUTE_ATTRIBUTE), function

  def iter_handlers(self):
    for function in self.iter_callables():
      if hasattr(function, self.INSTALL_ATTRIBUTE):
        yield getattr(function, self.INSTALL_ATTRIBUTE), function

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
    self._context.send(to, method, body)

  def link(self, to):
    self._assert_bound()
    self._context.link(self.pid, to)

  def terminate(self):
    self._assert_bound()
    self._context.terminate(self.pid)


class ProtobufProcess(Process):
  @classmethod
  def install(cls, message_type, endpoint=None):
    endpoint = endpoint or message_type.__class__.__name__
    def wrap(fn):
      setattr(fn, cls.MESSAGE_TYPE_ATTRIBUTE, message_type)
      return Process.install(endpoint)(fn)
    return wrap

  def send(self, to, message, method_name=None):
    super(ProtobufProcess, self).send(
        to, method_name or message.__class__.__name__, message.SerializeToString())

  def handle_message(self, name, from_pid, body):
    handler = self._message_handlers[name]
    message_type = getattr(handler, self.MESSAGE_TYPE_ATTRIBUTE)
    message = message_type()
    message.MergeFromString(body)
    super(ProtobufProcess, self).handle_message(name, from_pid, body)


"""
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


class ExecutorProcess(ProtobufProcess):
  def __init__(self, slave_pid, driver, executor):
    self.slave_pid = slave_pid
    self.driver = driver
    self.executor = executor
    super(SlaveProcess, self).__init__('slave')

  def initialize(self):
    regiser_executor_message = RegisterExecutorMessage(framework_id, executor_id)
    self.send(
        self.slave_pid,
        register_executor_message,
        method_name='mesos.internal.RegisterExecutorMessage')

  @install(ExecutorRegisteredMessage, endpoint='mesos.internal.ExecutorRegisteredMessage')
  def registered(self, message):
    executor_info, framework_id, framework_info, slave_id, slave_info = (
        message.executor_info, message.framework_id, message.framework_info, message.slave_id,
        message.slave_info)
    # stuff

  @route('/vars.json')
  def vars(self, handler):
    handler.write(json.dumps(self._vars))

  @route('/expensive')
  @asynchronous
  def vars(self, handler):
    result1 = yield self.some_expensive_op1()
    result2 = yield self.some_expensive_op2(result1)
    handler.write(result2.serialize())

  @route('/redirect_me')
  def redirector(self, handler):
    handler.redirect('some_other_url')



slave = PID.from_string(sys.argv[1])
executor_process = ExecutorProcess(slave, driver, executor)
context.spawn(executor_process)

"""
