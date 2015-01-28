import logging
import os
import threading

from compactor.context import Context
from compactor.pid import PID
from compactor.process import Process

import pytest


logging.basicConfig()


def test_ping():
  ping_pid = PID.from_string('(1)@%s:%s' % (
      os.getenv('PONGPROCESS_IP'),
      os.getenv('PONGPROCESS_PORT')))

  class PongProcess(Process):
    def __init__(self, **kw):
      self.event = threading.Event()
      super(PongProcess, self).__init__('ponger', **kw)

    @Process.install('/pong')
    def pong(self, handler):
      self.event.set()

  context = Context()
  context.start()

  pong = PongProcess()
  pong_pid = context.spawn(pong)
  context.send(pong_pid, ping_pid, 'ping')

  pong.event.wait(timeout=1.0)
  assert pong.event.is_set()

  context.stop()
