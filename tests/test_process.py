import uuid
import threading

from compactor.context import Context
from compactor.process import Process


import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def test_simple_process():
  parameter = []
  event = threading.Event()

  class DerpProcess(Process):
    def __init__(self, **kw):
      super(DerpProcess, self).__init__('derp', **kw)

    @Process.install('ping')
    def ping(self, value):
      parameter.append(value)
      event.set()

  context = Context()
  context.start()

  derp = DerpProcess()
  pid = context.spawn(derp)
  context.dispatch(pid, 'ping', 42)

  event.wait(timeout=1.0)
  assert event.is_set()
  assert parameter == [42]

  context.stop()


MAX_TIMEOUT = 10


def test_link_race_condition():
  context1 = Context()
  context1.start()

  context2 = Context()
  context2.start()

  class Leader(Process):
    def __init__(self):
      super(Leader, self).__init__('leader')
      self.uuid = None

    @Process.install('register')
    def register(self, from_pid, uuid):
      log.debug('Leader::register(%s, %s)' % (from_pid, uuid))
      self.send(from_pid, 'registered', uuid)

  class Follower(Process):
    def __init__(self, leader):
      super(Follower, self).__init__('follower')
      self.leader = leader
      self.uuid = uuid.uuid4().bytes
      self.registered = threading.Event()

    def initialize(self):
      super(Follower, self).initialize()
      self.link(self.leader.pid)
      self.send(self.leader.pid, 'register', self.uuid)

    @Process.install('registered')
    def registered(self, from_pid, uuid):
      log.debug('Follower::registered(%s, %s)' % (from_pid, uuid))
      assert uuid == self.uuid
      assert from_pid == self.leader.pid
      self.registered.set()

  leader = Leader()
  context1.spawn(leader)

  follower = Follower(leader)
  context2.spawn(follower)

  follower.registered.wait(timeout=MAX_TIMEOUT)
  assert follower.registered.is_set()

  context1.stop()
  context2.stop()
