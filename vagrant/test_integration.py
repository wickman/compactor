import logging
import os
import subprocess
import threading
import unittest

from compactor.context import Context
from compactor.pid import PID
from compactor.process import Process

import pytest


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class TestVagrantIntegration(unittest.TestCase):
  def setUp(self):
    self.__pong = subprocess.Popen(
        'vagrant ssh -- LIBPROCESS_IP=192.168.33.2 LIBPROCESS_PORT=31337 GLOG_v=5 ./pong',
        shell=True)
    self.ping_pid = PID.from_string('(1)@192.168.33.2:31337')
    self.context = Context(ip='192.168.33.1')
    self.context.start()

  def tearDown(self):
    self.__pong.kill()
    self.context.stop()

  def test_ping(self):
    class PongProcess(Process):
      def __init__(self, **kw):
        self.event = threading.Event()
        super(PongProcess, self).__init__('ponger', **kw)

      @Process.install('pong')
      def pong(self, from_pid, body):
        print('from_pid: %r, body: %r' % (from_pid, body))
        self.event.set()

    pong = PongProcess()
    pong_pid = self.context.spawn(pong)
    self.context.send(pong_pid, self.ping_pid, 'ping')

    pong.event.wait(timeout=10.0)
    assert pong.event.is_set()
