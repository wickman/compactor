import time
from compactor.process import Process
from compactor.context import Context


import logging
logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class WebProcess(Process):

  @Process.install('ping')
  def ping(self, from_pid, body):
    log.info("Received ping")

    def respond():
      time.sleep(0.5)
      self.send(from_pid, "pong")
    self.context.loop.add_callback(respond)

  @Process.install('pong')
  def pong(self, from_pid, body):
    log.info("Received pong")

    def respond():
      time.sleep(0.5)
      self.send(from_pid, "ping")
    self.context.loop.add_callback(respond)


def listen(identifier):
  """
  Launch a listener and return the compactor context.
  """

  context = Context()
  process = WebProcess(identifier)

  context.spawn(process)

  log.info("Launching PID %s", process.pid)

  return process, context


if __name__ == '__main__':

  a, a_context = listen("web(1)")
  b, b_context = listen("web(2)")

  a_context.start()
  b_context.start()

  # Kick off the game of ping/pong by sending a message to B from A
  a.send(b.pid, "ping")

  while a_context.isAlive() or b_context.isAlive():
    time.sleep(0.5)
