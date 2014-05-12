from __future__ import absolute_import

import logging
import re
import types

from .pid import PID

from tornado import gen
from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, Application, HTTPError

log = logging.getLogger(__name__)


class ProcessBaseHandler(RequestHandler):
  def initialize(self, process=None):
    self.process = process


class WireProtocolMessageHandler(ProcessBaseHandler):
  """Tornado request handler for libprocess internal messages."""
  OK_RESPONSE = 202
  LEGACY_RESPONSE = 204

  @classmethod
  def detect_process(cls, headers):
    """Returns tuple of process, legacy or None, None if not process originating."""
    def extract():
      if 'Libprocess-From' in headers:
        return PID.from_string(headers['Libprocess-From']), False
      elif 'User-Agent' in headers and headers['User-Agent'].startswith('libprocess/'):
        return PID.from_string(headers['User-Agent'][len('libprocess/'):]), True
      else:
        return None, None
    try:
      return extract()
    except ValueError:
      return None, None

  def initialize(self, **kw):
    self.__name = kw.pop('name')
    super(WireProtocolMessageHandler, self).initialize(**kw)

  def flush(self, *args, **kw):
    """Trap flush for libprocess wire messages so that response is possibly not sent."""
    quiet = self.get_status() == self.LEGACY_RESPONSE

    if quiet:
      # clear -- do not send a response.
      self.clear()
    else:
      super(WireProtocolMessageHandler, self).flush(*args, **kw)

  def post(self, *args, **kw):
    log.info('Handling %s for %s' % (self.__name, self.process))

    process, legacy = self.detect_process(self.request.headers)

    if process is None:
      self.set_status(404)
      return

    log.info('Delivering %s to %s from %s' % (self.__name, self.process, process))
    log.info('Request body length: %s' % len(self.request.body))
    self.process.handle_message(self.__name, process, self.request.body)

    # set status to 204 if legacy.  it will be intercepted in flush().
    self.set_status(self.LEGACY_RESPONSE if legacy else self.OK_RESPONSE)


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
    """Construct an HTTP server on a socket given an ioloop."""
    self.loop = loop
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
           dict(process=process, name=message_name))
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
