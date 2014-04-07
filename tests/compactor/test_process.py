import threading

from compactor.context import Context
from compactor.process import Process


def test_simple_process():
  event = threading.Event()

  class DerpProcess(Process):
    def __init__(self, **kw):
      super(DerpProcess, self).__init__('derp', **kw)
    
    def ping(self):
      event.set()

  context = Context()
  context.start()
  context.wait_started()
  
  derp = DerpProcess(context=context)
  pid = context.spawn(derp)
  context.dispatch(pid, 'ping')
  
  event.wait(timeout=1.0)
  assert event.is_set()

  context.stop()
