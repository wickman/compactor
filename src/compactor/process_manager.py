import logging
import threading

from .event import TerminatedEvent

log = logging.getLogger(__name__)


class ProcessManager(object):
  EMPTY_DELAY_SECS = 0.01  # 10ms

  def __init__(self, context):
    self.context = context
    self.delegate = context.delegate
    self.processes = {}
    self.runq = []
    self.context.loop.call_soon(self.schedule)
    self._run_condition = threading.Condition()

  def spawn(self, process):
    if process.pid in self.processes:
      raise RuntimeError('Cannot spawn already-spawned process.')
    self.processes[process.pid] = process
    self.enqueue(process)  # Enqueue process to be initialized
    return process.pid

  def schedule_one(self):
    with self._run_condition:
      if self.runq:
        self.resume(self.runq.pop(0))
        return True
    return False

  def schedule(self):
    if self.schedule_one():
      self.context.loop.call_soon(self.schedule)
    else:
      self.context.loop.call_later(self.EMPTY_DELAY_SECS, self.schedule)

  def enqueue(self, process):
    with self._run_condition:
      self.runq.append(process)
      self._run_condition.notify_all()

  def deliver(self, pid, event):
    self.processes[pid].enqueue(event)

  def resume(self, process):
    if process.state not in (process.State.BOTTOM, process.State.READY):
      raise RuntimeError('Resuming a process not in BOTTOM/READY states.')

    blocked = terminate = False

    if process.state is process.State.BOTTOM:
      process.state = process.State.RUNNING
      try:
        process.initialize()
      except Exception as e:
        # log exception
        terminate = True

    event = None
    while not terminate and not blocked:
      with process.lock:
        if process.events:
          event = process.events.pop(0)
          process.state = process.State.RUNNING
        else:
          process.state = process.State.BLOCKED
          blocked = True

      if blocked:
        continue

      # consider adding event filtering here
      terminate = isinstance(event, TerminatedEvent)

      try:
        process.serve(event)
      except Exception as e:
        # log exception
        terminate = True

      if terminate:
        # do cleanup?
        pass
