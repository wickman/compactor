class Event(object):
  pass


class MessageEvent(Event):
  def __init__(self, message):
    self.message = message
    super(MessageEvent, self).__init__()


class HttpEvent(Event):
  def __init__(self, socket, request):
    self.socket, self.request = socket, request
    super(HttpEvent, self).__init__()


class DispatchEvent(Event):
  def __init__(self, name, args):
    self.name, self.args = name, args
    super(DispatchEvent, self).__init__()


class ExitedEvent(Event):
  def __init__(self, pid):
    self.pid = pid
    super(ExitedEvent, self).__init__()


class TerminatedEvent(Event):
  def __init__(self, from_):
    self.from_ = from_
    super(TerminatedEvent, self).__init__()
