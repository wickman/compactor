# SocketManager is probably where special implementation logic should live, e.g.
#   tornado
#   gevent
#   stdlib/threading

class SocketManager(object):
  def __init__(self, loop):
    self.loop = loop

  # def accepted(self, socket:socket)
  # def link(self, process:process, to:pid)
  # def proxy(self, socket:socket)
  #  -> http req/resp serializer
  #
  # def send(self, encoder, persist)
  # def send(self, response, request, socket)
  # def send(self, message)
  #
  # def next
  # def close
  # def exited(node)
  # def exited(process)
