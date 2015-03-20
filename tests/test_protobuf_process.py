import threading

from compactor.context import Context
from compactor.process import ProtobufProcess

import pytest

try:
  import mock
except ImportError:
  from unittest import mock

try:
  import google.protobuf
  HAS_PROTOBUF=True
except ImportError:
  HAS_PROTOBUF=False

import logging
logging.basicConfig()


@pytest.mark.skipif('not HAS_PROTOBUF')
def test_protobuf_process():
  parameter = []
  event = threading.Event()

  recv_msg = mock.MagicMock()
  recv_msg.MergeFromString = mock.MagicMock()

  def msg_init():
    return recv_msg

  send_msg = mock.MagicMock()
  send_msg.SerializeToString = mock.MagicMock()
  send_msg.SerializeToString.return_value = b'beepboop'

  class Pinger(ProtobufProcess):
    @ProtobufProcess.install(msg_init, endpoint='foo.bar.ping')
    def ping(self, from_pid, message):
      assert message == recv_msg
      message.MergeFromString.assert_called_with(b'beepboop')
      event.set()

  class Ponger(ProtobufProcess):
    pass

  context = Context()
  context.start()
  pinger = Pinger('pinger')
  ping_pid = context.spawn(pinger)

  context2 = Context()
  context2.start()
  ponger = Ponger('ponger')
  pong_pid = context2.spawn(ponger)

  # TODO(wickman) this doesn't actually work for local processes, hence
  # spawning two separate contexts.
  ponger.send(ping_pid, send_msg, method_name='foo.bar.ping')

  event.wait(timeout=1)
  assert event.is_set()

  context.stop()
  context2.stop()


@pytest.mark.skipif('not HAS_PROTOBUF')
def test_protobuf_process_local_dispatch():
  parameter = []
  event = threading.Event()

  recv_msg = mock.MagicMock()
  recv_msg.MergeFromString = mock.MagicMock()

  def msg_init():
    return recv_msg

  send_msg = mock.MagicMock()
  send_msg.SerializeToString = mock.MagicMock()
  send_msg.SerializeToString.return_value = b'beepboop'

  class Pinger(ProtobufProcess):
    @ProtobufProcess.install(msg_init, endpoint='foo.bar.ping')
    def ping(self, from_pid, message):
      assert message == recv_msg
      message.MergeFromString.assert_called_with(b'beepboop')
      event.set()

  class Ponger(ProtobufProcess):
    pass

  context = Context()
  context.start()

  pinger = Pinger('pinger')
  ping_pid = context.spawn(pinger)
  ponger = Ponger('ponger')
  pong_pid = context.spawn(ponger)

  ponger.send(ping_pid, send_msg, method_name='foo.bar.ping')

  event.wait(timeout=1)
  assert event.is_set()

  context.stop()
