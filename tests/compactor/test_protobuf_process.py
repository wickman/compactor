import threading

from compactor.context import Context
from compactor.process import ProtobufProcess

try:
  import mock
except ImportError:
  from unittest import mock

import logging
logging.basicConfig()


def test_protobuf_process():
  parameter = []
  event = threading.Event()

  recv_msg = mock.MagicMock()
  recv_msg.MergeFromString = mock.MagicMock()

  def msg_init():
    return recv_msg

  send_msg = mock.MagicMock()
  send_msg.SerializeToString = mock.MagicMock()
  send_msg.SerializeToString.return_value = 'beepboop'

  class Pinger(ProtobufProcess):
    @ProtobufProcess.install(msg_init, endpoint='foo.bar.ping')
    def ping(self, from_pid, message):
      assert message == recv_msg
      message.MergeFromString.assert_called_with('beepboop')
      event.set()

  context = Context()
  context.start()

  pinger = Pinger('pinger')
  pid = context.spawn(pinger)
  pinger.send(pid, send_msg, 'foo.bar.ping')

  event.wait(timeout=1)
  assert event.is_set()

  context.stop()
