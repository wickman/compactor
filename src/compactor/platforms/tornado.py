from __future__ import absolute_import

import socket

from ..socket_manager import SocketManager

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.platform.asyncio import BaseAsyncIOLoop


class TornadoSocketManager(SocketManager):
  @classmethod
  def make_socket(cls):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('localhost', 0))
    return s

  def __init__(self, context):
    self.context = context
    class CustomIOLoop(BaseAsyncIOLoop):
      def initialize(self):
        super(CustomIOLoop, self).initialize(context.loop, close_loop=False)
    self._loop = CustomIOLoop()
    self.server = HTTPServer(self.handle_request, io_loop=self._loop)
    self.ip, self.port, self.socket = None, None, None

  def allocate_listener(self):
    sock = self.make_socket()
    ip, port = sock.getsockname()
    if ip == '127.0.0.1':
      ip = socket.gethostbyname(socket.gethostname())
    self.ip, self.port = ip, port
    self.socket = sock
    self.socket.listen(1024)
    self.server.add_sockets([sock])
    return self.ip, self.port

  def handle_request(self, request):
    pass
