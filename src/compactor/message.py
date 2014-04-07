class Message(object):
  __slots__ = ('name', 'from_', 'to', 'body')

  def __init__(self, name, from_, to, body):
    # TODO typecheck
    self.name, self.from_, self.to, self.body = name, from_, to, body

  def __iter__(self):
    return iter((self.name, self.from_, self.to, self.body))
