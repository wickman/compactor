import threading

from compactor.context import Context
from compactor.process import Process


import logging
logging.basicConfig()


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
