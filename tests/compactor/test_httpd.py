import logging
import threading

import compactor
from compactor.context import Context
from compactor.process import Process

import requests

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class PingPongProcess(Process):
  def __init__(self, **kw):
    self.ping_event = threading.Event()
    super(PingPongProcess, self).__init__('pingpong', **kw)

  @Process.route('/ping')
  def ping(self, handler):
    self.ping_event.set()
    handler.write('pong')


def test_simple_routed_process():
  context = Context()
  context.start()

  ping = PingPongProcess()
  pid = context.spawn(ping)

  url = 'http://%s:%s/pingpong/ping' % (pid.ip, pid.port)
  content = requests.get(url).text
  assert content == 'pong'
  assert ping.ping_event.is_set()

  context.stop()


def test_mount_unmount():
  context = Context()
  context.start()

  # no mounts
  url = 'http://%s:%s' % (context.ip, context.port)
  response = requests.get(url)
  assert response.status_code == 404

  # unmounted process
  url = 'http://%s:%s/pingpong/ping' % (context.ip, context.port)
  response = requests.get(url)
  assert response.status_code == 404

  # mount
  ping = PingPongProcess()
  pid = context.spawn(ping)

  response = requests.get(url)
  assert response.status_code == 200
  assert response.text == 'pong'

  # unmount
  context.terminate(pid)
  response = requests.get(url)
  assert response.status_code == 404

  context.stop()


class Web(Process):
  def __init__(self, name, **kw):
    super(Web, self).__init__(name, **kw)

  def write_pong(self, handler, callback=None):
    handler.write('pong')
    if callback:
      callback()

  @Process.route('/ping')
  def ping(self, handler):
    yield compactor.task(self.write_pong, handler)


def test_async_route():
  context = Context()
  context.start()

  web = Web('web')
  pid = context.spawn(web)

  url = 'http://%s:%s/web/ping' % (pid.ip, pid.port)
  content = requests.get(url).text
  assert content == 'pong'

  context.stop()


def test_simple_message():
  class PingPongProcess(Process):
    def __init__(self, name, **kw):
      self.ping_event = threading.Event()
      self.pong_event = threading.Event()
      super(PingPongProcess, self).__init__(name, **kw)

    @Process.install('ping')
    def ping(self, from_pid, body):
      self.ping_event.set()
      log.info('%s got ping' % self.pid)
      self.send(from_pid, 'pong')

    @Process.install('pong')
    def pong(self, from_pid, body):
      log.info('%s got pong' % self.pid)
      self.pong_event.set()

  context = Context()
  context.start()

  proc1 = PingPongProcess('proc1')
  proc2 = PingPongProcess('proc2')

  pid1 = context.spawn(proc1)
  pid2 = context.spawn(proc2)

  proc1.send(pid2, 'ping')
  proc1.pong_event.wait(timeout=1)
  assert proc1.pong_event.is_set()
  assert proc2.ping_event.is_set()

  context.stop()
