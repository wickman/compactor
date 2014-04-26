import threading

from compactor.context import Context
from compactor.process import Process

import requests

import logging
logging.basicConfig()


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
