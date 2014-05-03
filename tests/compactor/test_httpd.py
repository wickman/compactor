import logging
import threading

import compactor
from compactor.context import Context
from compactor.process import Process
from compactor.testing import ephemeral_context, EphemeralContextTestCase

import requests
import pytest

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
    yield compactor.task(self.write_pong, handler)


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
  def __init__(self, to_pid, iterations, context):
    self.success = False
    self.context = context
    self.to_pid = to_pid
    self.iterations = iterations
    super(ScatterThread, self).__init__()

  def run(self):
    scatter = ScatterProcess('scatter' + self.context.unique_suffix())
    self.context.spawn(scatter)

    expected_acks = set('syn%d' % k for k in range(self.iterations))

    for k in range(self.iterations):
      scatter.send(self.to_pid, 'syn', 'syn%d' % k)

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


@pytest.mark.parametrize('gather_ack,scatter_ack', [
    (False, False),
    (False, True),
    (True, False),
    (True, True),
])
def test_multi_thread_multi_scatter(gather_ack, scatter_ack):
  with ephemeral_context(acks=gather_ack) as context:
    gather = GatherProcess()
    context.spawn(gather)
    scatters = [ScatterThread(gather.pid, 3, Context(acks=scatter_ack)) for k in range(5)]
    for scatter in scatters:
      scatter.context.start()
    try:
      startjoin(context, scatters)
    finally:
      for scatter in scatters:
        scatter.context.stop()


@pytest.mark.parametrize('acks', (False, True))
def test_single_thread_multi_scatter(acks):
  with ephemeral_context(acks=acks) as context:
    gather = GatherProcess()
    context.spawn(gather)
    scatters = [ScatterThread(gather.pid, 3, context) for k in range(5)]
    startjoin(context, scatters)


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

    proc1 = PingPongProcess('proc1')
    proc2 = PingPongProcess('proc2')

    pid1 = self.context.spawn(proc1)
    pid2 = self.context.spawn(proc2)

    proc1.send(pid2, 'ping')
    proc1.pong_event.wait(timeout=1)
    assert proc1.pong_event.is_set()
    assert proc2.ping_event.is_set()
