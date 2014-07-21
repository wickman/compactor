from __future__ import absolute_import

import logging
import re
import types
import time

from .pid import PID

from tornado import gen
from tornado import httputil
from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, Application, HTTPError

log = logging.getLogger(__name__)


class ProcessBaseHandler(RequestHandler):
  def initialize(self, process=None):
    self.process = process


class WireProtocolMessageHandler(ProcessBaseHandler):
  """Tornado request handler for libprocess internal messages."""

  @classmethod
  def detect_process(cls, headers):
    """Returns tuple of process, legacy or None, None if not process originating."""

    try:
      if 'Libprocess-From' in headers:
        return PID.from_string(headers['Libprocess-From']), False
      elif 'User-Agent' in headers and headers['User-Agent'].startswith('libprocess/'):
        return PID.from_string(headers['User-Agent'][len('libprocess/'):]), True
    except ValueError:
      pass

    return None, None

  def initialize(self, **kw):
    self.__name = kw.pop('name')
    super(WireProtocolMessageHandler, self).initialize(**kw)

  def set_default_headers(self):
    self._headers = httputil.HTTPHeaders({
      "Date": httputil.format_timestamp(time.time())
    })

  def post(self, *args, **kw):
    log.info('Handling %s for %s' % (self.__name, self.process.pid))

    process, legacy = self.detect_process(self.request.headers)

    if process is None:
      self.set_status(404)
      return

    log.debug('Delivering %s to %s from %s' % (self.__name, self.process.pid, process))
    log.debug('Request body length: %s' % len(self.request.body))

    # Handle the message
    self.process.handle_message(self.__name, process, self.request.body)

    self.set_status(202)
    self.finish()


class RoutedRequestHandler(ProcessBaseHandler):
  """Tornado request handler for routed http requests."""

  def initialize(self, **kw):
    self.__path = kw.pop('path')
    super(RoutedRequestHandler, self).initialize(**kw)

  @gen.engine
  def get(self, *args, **kw):
    log.info('Handling %s for %s' % (self.__path, self.process.pid))
    handle = self.process.handle_http(self.__path, self, *args, **kw)
    if isinstance(handle, types.GeneratorType):
      for stuff in handle:
        yield stuff
    self.finish()


class Blackhole(RequestHandler):
  def get(self):
    log.debug("Sending request to the black hole")
    raise HTTPError(404)


class HTTPD(object):
  """
  HTTP Server implementation that attaches to an event loop and socket, and
  is capable of handling mesos wire protocol messages.
  """

  def __init__(self, sock, loop):
    """
    Construct an HTTP server on a socket given an ioloop.
    """

    self.loop = loop
    self.sock = sock

    self.app = Application(handlers=[(r'/.*$', Blackhole)])
    self.server = HTTPServer(self.app, io_loop=self.loop)
    self.server.add_sockets([sock])

    self.sock.listen(1024)

  def terminate(self):
    log.info('Terminating HTTP server and all connections')

    self.server.close_all_connections()
    self.sock.close()

  def mount_process(self, process):
    """
    Mount a Process onto the http server to receive message callbacks.
    """

    for route_path in process.route_paths:
      route = '/%s%s' % (process.pid.id, route_path)
      log.info('Mounting route %s' % route)
      self.app.add_handlers('.*$', [(
        re.escape(route),
        RoutedRequestHandler,
        dict(process=process, path=route_path)
      )])

    for message_name in process.message_names:
      route = '/%s/%s' % (process.pid.id, message_name)
      log.info('Mounting message handler %s' % route)
      self.app.add_handlers('.*$', [(
        re.escape(route),
        WireProtocolMessageHandler,
        dict(process=process, name=message_name)
      )])

  def unmount_process(self, process):
    """
    Unmount a process from the http server to stop receiving message
    callbacks.
    """

    # There is no remove_handlers, but .handlers is public so why not.  server.handlers is a list of
    # 2-tuples of the form (host_pattern, [list of RequestHandler]) objects.  We filter out all
    # handlers matching our process from the RequestHandler list for each host pattern.
    def nonmatching(handler):
      return 'process' not in handler.kwargs or handler.kwargs['process'] != process

    def filter_handlers(handlers):
      host_pattern, handlers = handlers
      return (host_pattern, list(filter(nonmatching, handlers)))

    self.app.handlers = [filter_handlers(handlers) for handlers in self.app.handlers]
