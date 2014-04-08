# SocketManager is probably where special implementation logic should live, e.g.
#   tornado
#   gevent
#   stdlib/threading


from abc import abstractmethod
import socket

from twitter.common.lang import Interface


class SocketManager(Interface):
  @abstractmethod
  def allocate_listener(self):
    """Allocate the listening socket for the context.

    Returns a tuple of (ip, port).
    """

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



from .platforms.tornado import TornadoSocketManager
DEFAULT_SOCKET_MANAGER = TornadoSocketManager

