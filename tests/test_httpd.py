import logging
import threading

from compactor.context import Context
from compactor.process import Process
from compactor.testing import ephemeral_context, EphemeralContextTestCase

import requests
import pytest
from tornado import gen

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


class Web(Process):
  def __init__(self, name, **kw):
    super(Web, self).__init__(name, **kw)

  def write_pong(self, handler, callback=None):
    handler.write('pong')
    if callback:
      callback()

  @Process.route('/ping')
  def ping(self, handler):
    yield gen.Task(self.write_pong, handler)


class ScatterProcess(Process):
  def __init__(self, name):
    self.acks = []
    self.condition = threading.Condition()
    super(ScatterProcess, self).__init__(name)

  @Process.install('ack')
  def ack(self, from_pid, body):
    with self.condition:
      self.acks.append(body)
      self.condition.notify_all()


class GatherProcess(Process):
  def __init__(self):
    self.messages = []
    super(GatherProcess, self).__init__('gather')

  @Process.install('syn')
  def syn(self, from_pid, body):
    self.messages.append(body)
    self.send(from_pid, 'ack', body)


class ScatterThread(threading.Thread):
  SUFFIX_ID = 1
  SUFFIX_LOCK = threading.Lock()

  def __init__(self, to_pid, iterations, context):
    self.success = False
    self.context = context
    self.to_pid = to_pid
    self.iterations = iterations
    super(ScatterThread, self).__init__()

  def run(self):
    with ScatterThread.SUFFIX_LOCK:
      suffix = ScatterThread.SUFFIX_ID
      ScatterThread.SUFFIX_ID += 1
    scatter = ScatterProcess('scatter(%d)' % suffix)
    self.context.spawn(scatter)

    expected_acks = set(('syn%d' % k).encode('utf8') for k in range(self.iterations))

    for k in range(self.iterations):
      scatter.send(self.to_pid, 'syn', ('syn%d' % k).encode('utf8'))

    while True:
      with scatter.condition:
        if set(scatter.acks) == expected_acks:
          break

    self.success = True


def startjoin(context, scatters):
  gather = GatherProcess()
  context.spawn(gather)

  for scatter in scatters:
    scatter.start()

  for scatter in scatters:
    scatter.join()

  for scatter in scatters:
    assert scatter.success


def test_multi_thread_multi_scatter():
  with ephemeral_context() as context:
    gather = GatherProcess()
    context.spawn(gather)
    scatters = [ScatterThread(gather.pid, 3, Context()) for k in range(5)]
    for scatter in scatters:
      scatter.context.start()
    try:
      startjoin(context, scatters)
    finally:
      for scatter in scatters:
        scatter.context.stop()


def test_single_thread_multi_scatter():
  with ephemeral_context() as context:
    gather = GatherProcess()
    context.spawn(gather)
    scatters = [ScatterThread(gather.pid, 3, context) for k in range(5)]
    startjoin(context, scatters)


class ChildProcess(Process):
  def __init__(self):
    self.exit_event = threading.Event()
    self.link_event = threading.Event()
    self.parent_pid = None
    super(ChildProcess, self).__init__('child')

  @Process.install('link_me')
  def link_me(self, from_pid, body):
    log.info('Got link request')
    self.parent_pid = from_pid
    log.info('Sending link')
    self.link(from_pid)
    log.info('Sent link')
    self.link_event.set()
    log.info('Set link event')

  def exited(self, pid):
    log.info('ChildProcess got exited event for %s' % pid)
    if pid == self.parent_pid:
      self.exit_event.set()


class ParentProcess(Process):
  def __init__(self):
    super(ParentProcess, self).__init__('parent')

  def exited(self, pid):
    log.info('ParentProcess got exited event for %s' % pid)


class TestHttpd(EphemeralContextTestCase):
  def test_simple_routed_process(self):
    ping = PingPongProcess()
    pid = self.context.spawn(ping)

    url = 'http://%s:%s/pingpong/ping' % (pid.ip, pid.port)
    content = requests.get(url).text
    assert content == 'pong'
    assert ping.ping_event.is_set()

  def test_mount_unmount(self):
    # no mounts
    url = 'http://%s:%s' % (self.context.ip, self.context.port)
    response = requests.get(url)
    assert response.status_code == 404

    # unmounted process
    url = 'http://%s:%s/pingpong/ping' % (self.context.ip, self.context.port)
    response = requests.get(url)
    assert response.status_code == 404

    # mount
    ping = PingPongProcess()
    pid = self.context.spawn(ping)

    response = requests.get(url)
    assert response.status_code == 200
    assert response.text == 'pong'

    # unmount
    self.context.terminate(pid)
    response = requests.get(url)
    assert response.status_code == 404

  def test_async_route(self):
    web = Web('web')
    pid = self.context.spawn(web)

    url = 'http://%s:%s/web/ping' % (pid.ip, pid.port)
    content = requests.get(url).text
    assert content == 'pong'

  def test_simple_message(self):
    class PingPongProcess(Process):
      def __init__(self, name, **kw):
        self.ping_event = threading.Event()
        self.ping_body = None
        self.pong_event = threading.Event()
        self.pong_body = None
        super(PingPongProcess, self).__init__(name, **kw)

      @Process.install('ping')
      def ping(self, from_pid, body):
        self.ping_body = body
        self.ping_event.set()
        log.info('%s got ping' % self.pid)
        self.send(from_pid, 'pong', body=body)

      @Process.install('pong')
      def pong(self, from_pid, body):
        log.info('%s got pong' % self.pid)
        self.pong_body = body
        self.pong_event.set()

    proc1 = PingPongProcess('proc1')
    proc2 = PingPongProcess('proc2')
    self.context.spawn(proc1)
    pid2 = self.context.spawn(proc2)

    # ping with body
    proc1.send(pid2, 'ping', b'with_body')
    proc1.pong_event.wait(timeout=1)
    assert proc1.pong_event.is_set()
    assert proc2.ping_event.is_set()
    assert proc1.pong_body == b'with_body'
    assert proc2.ping_body == b'with_body'

    proc1.pong_event.clear()
    proc2.ping_event.clear()

    # ping without body
    proc1.send(pid2, 'ping')
    proc1.pong_event.wait(timeout=1)
    assert proc1.pong_event.is_set()
    assert proc2.ping_event.is_set()
    assert proc1.pong_body == b''
    assert proc2.ping_body == b''

  # Not sure why this doesn't work.
  @pytest.mark.xfail
  def test_link_exit_remote(self):
    parent_context = Context()
    parent_context.start()
    parent = ParentProcess()
    parent_context.spawn(parent)

    child = ChildProcess()
    self.context.spawn(child)

    parent.send(child.pid, 'link_me')

    child.link_event.wait(timeout=1.0)
    assert child.link_event.is_set()
    assert not child.exit_event.is_set()

    parent_context.terminate(parent.pid)
    parent_context.stop()

    child.send(parent.pid, 'this_will_break')
    child.exit_event.wait(timeout=1)
    assert child.exit_event.is_set()

  def test_link_exit_local(self):
    parent = ParentProcess()
    self.context.spawn(parent)
    child = ChildProcess()
    self.context.spawn(child)

    parent.send(child.pid, 'link_me')
    child.link_event.wait(timeout=1.0)
    assert child.link_event.is_set()
    assert not child.exit_event.is_set()

    log.info('*** Terminating parent.pid')
    self.context.terminate(parent.pid)
    child.exit_event.wait(timeout=1)
    assert child.exit_event.is_set()
