import threading

from compactor.context import Context
from compactor.process import Process

import requests

import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)




def test_simple_routed_process():
  class PingPongProcess(Process):
    def __init__(self, **kw):
      self.ping_event = threading.Event()
      super(PingPongProcess, self).__init__('pingpong', **kw)

    @Process.route('/ping')
    def ping(self, handler):
      self.ping_event.set()
      handler.write('pong')

  context = Context()
  context.start()

  ping = PingPongProcess()
  pid = context.spawn(ping)

  url = 'http://%s:%s/pingpong/ping' % (pid.ip, pid.port)
  content = requests.get(url).text
  assert content == 'pong'
  assert ping.ping_event.is_set()

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

  context1 = Context()
  context1.start()
  context2 = Context()
  context2.start()

  proc1 = PingPongProcess('proc1')
  proc2 = PingPongProcess('proc2')

  pid1 = context1.spawn(proc1)
  pid2 = context2.spawn(proc2)

  proc1.send(pid2, 'ping')
  proc1.pong_event.wait(timeout=60)
  assert proc1.pong_event.is_set()
  assert proc2.ping_event.is_set()

  context1.stop()
  context2.stop()
