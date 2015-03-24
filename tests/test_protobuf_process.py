import threading

from compactor.context import Context
from compactor.process import ProtobufProcess

import pytest

try:
  from google.protobuf import descriptor_pb2
  HAS_PROTOBUF = True
except ImportError:
  HAS_PROTOBUF = False

import logging
logging.basicConfig()
LOOPBACK = '127.0.0.1'


# Send from one to another, swap out contexts to test local vs remote dispatch.
def ping_pong(context1, context2):
  ping_calls = []
  event = threading.Event()

  class Pinger(ProtobufProcess):
    @ProtobufProcess.install(descriptor_pb2.DescriptorProto)
    def ping(self, from_pid, message):
      ping_calls.append((from_pid, message))
      event.set()

  class Ponger(ProtobufProcess):
    pass

  pinger = Pinger('pinger')
  ponger = Ponger('ponger')

  ping_pid = context1.spawn(pinger)
  pong_pid = context2.spawn(ponger)

  send_msg = descriptor_pb2.DescriptorProto()
  send_msg.name = 'ping'

  ponger.send(ping_pid, send_msg)

  event.wait(timeout=1)
  assert event.is_set()
  assert len(ping_calls) == 1
  from_pid, message = ping_calls[0]
  assert from_pid == pong_pid
  assert message == send_msg


@pytest.mark.skipif('not HAS_PROTOBUF')
def test_protobuf_process_remote_dispatch():
  context1 = Context(ip=LOOPBACK)
  context1.start()

  context2 = Context(ip=LOOPBACK)
  context2.start()

  try:
    ping_pong(context1, context2)
  finally:
    context1.stop()
    context2.stop()


@pytest.mark.skipif('not HAS_PROTOBUF')
def test_protobuf_process_local_dispatch():
  context = Context(ip=LOOPBACK)
  context.start()

  try:
    ping_pong(context, context)
  finally:
    context.stop()
