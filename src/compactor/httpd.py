from __future__ import absolute_import

import socket

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.platform.asyncio import BaseAsyncIOLoop

from tornado.tcpserver import TCPServer
from tornado.httpserver import HTTPConnection



class SocketManager(object):
  # context 

  pass
  


class HTTPD(TCPServer):                                                                                                                           self.no_keep_alive,
  def __init__(self,
               request_callback,
               no_keep_alive=False,
               io_loop=None,
               xheaders=False,
               ssl_options=None,
               protocol=None,
               **kwargs):
    self.request_callback = request_callback
    self.no_keep_alive = no_keep_alive
    self.xheaders = xheaders
    self.protocol = protocol
    super(HTTPD, self).__init__(io_loop=io_loop, ssl_options=ssl_options, **kwargs)

  def handle_stream(self, stream, address):
    connection = HTTPConnection(stream, address, self.request_callback, self.no_keep_alive,
                     self.xheaders,
                     self.protocol)                                                                                                                           self.xheaders,
                                                                                                                           self.protocol)


class HTTPD(object):
  def __init__(self, sock, request_handler, loop):
    class CustomIOLoop(BaseAsyncIOLoop):
      def initialize(self):
        super(CustomIOLoop, self).initialize(loop, close_loop=False)
    self.loop = CustomIOLoop()
    self.server = HTTPServer(request_handler, io_loop=self.loop, )
    self.server.add_sockets([sock])
    sock.listen(1024)
