import logging
import os
import threading

from compactor.context import Context
from compactor.pid import PID
from compactor.process import Process

import pytest


logging.basicConfig()


@pytest.mark.skipif('os.getenv("MESOS_SLAVE_PID") is None')
def test_slave_ping():
  slave_pid = PID.from_string(os.getenv("MESOS_SLAVE_PID"))

  class PongProcess(Process):
    def __init__(self, **kw):
      self.event = threading.Event()
      super(PongProcess, self).__init__('ponger', **kw)

    @Process.route('/PONG')
    def pong(self, handler):
      self.event.set()

  context = Context()
  context.start()

  pong = PongProcess()
  pong_pid = context.spawn(pong)
  context.send(pong_pid, slave_pid, 'PING')

  pong.event.wait(timeout=1.0)
  assert pong.event.is_set()

  context.stop()
