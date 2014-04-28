from __future__ import absolute_import

import logging
import re
import socket
import types

from .pid import PID

from tornado import gen
from tornado.httpserver import HTTPConnection, HTTPServer
from tornado.ioloop import IOLoop
from tornado.platform.asyncio import BaseAsyncIOLoop
from tornado.tcpserver import TCPServer
from tornado.web import asynchronous, RequestHandler, Application, HTTPError

log = logging.getLogger(__name__)


class ProcessBaseHandler(RequestHandler):
  def initialize(self, process=None):
    self.process = process


class WireProtocolMessageHandler(ProcessBaseHandler):
  """Tornado request handler for libprocess internal messages."""

  def initialize(self, **kw):
    self.__name = kw.pop('name')
    super(WireProtocolMessageHandler, self).initialize(**kw)

  def flush(self, *args, **kw):
    """Trap flush for libprocess wire messages so that responses are not sent."""
    pass

  def post(self, *args, **kw):
    log.info('Handling %s for %s' % (self.__name, self.process))
    user_agent = self.request.headers['User-Agent']
    if not user_agent.startswith('libprocess/'):
      return
    try:
      from_pid = PID.from_string(user_agent[len('libprocess/'):])
    except ValueError:
      log.error('Unknown process user agent: %s' % user_agent)
      return
    log.info('Delivering %s to %s from %s' % (self.__name, self.process, from_pid))
    self.process.handle_message(self.__name, from_pid, self.request.body)


class RoutedRequestHandler(ProcessBaseHandler):
  """Tornado request handler for routed http requests."""

  def initialize(self, **kw):
    self.__path = kw.pop('path')
    super(RoutedRequestHandler, self).initialize(**kw)

  @gen.engine
  def get(self, *args, **kw):
    log.info('Handling %s for %s' % (self.__path, self.process))
    handle = self.process.handle_http(self.__path, self, *args, **kw)
    if isinstance(handle, types.GeneratorType):
      for stuff in handle:
        yield stuff
    self.finish()


class Blackhole(RequestHandler):
  def get(self):
    raise HTTPError(404)


class HTTPD(object):
  def __init__(self, sock, loop):
    class CustomIOLoop(BaseAsyncIOLoop):
      def initialize(self):
        super(CustomIOLoop, self).initialize(loop, close_loop=False)
    self.loop = CustomIOLoop()
    self.app = Application(handlers=[(r'/.*$', Blackhole)])
    self.server = HTTPServer(self.app, io_loop=self.loop)
    self.server.add_sockets([sock])
    sock.listen(1024)

  def mount_process(self, process):
    for route_path in process.route_paths:
      route = '/%s%s' % (process.pid.id, route_path)
      log.info('Mounting route %s' % route)
      self.app.add_handlers('.*$', [
          (re.escape(route),
           RoutedRequestHandler,
           dict(process=process, path=route_path)),
      ])

    for message_name in process.message_names:
      route = '/%s/%s' % (process.pid.id, message_name)
      log.info('Mounting message handler %s' % route)
      self.app.add_handlers('.*$', [
          (re.escape(route),
           WireProtocolMessageHandler,
           dict(process=process, name=message_name)),
      ])

  def unmount_process(self, process):
    # There is no remove_handlers, but .handlers is public so why not.  server.handlers is a list of
    # 2-tuples of the form (host_pattern, [list of RequestHandler]) objects.  We filter out all
    # handlers matching our process from the RequestHandler list for each host pattern.
    def nonmatching(handler):
      return 'process' not in handler.kwargs or handler.kwargs['process'] != process
    def filter_handlers(handlers):
      host_pattern, handlers = handlers
      return (host_pattern, list(filter(nonmatching, handlers)))
    self.app.handlers = [filter_handlers(handlers) for handlers in self.app.handlers]
