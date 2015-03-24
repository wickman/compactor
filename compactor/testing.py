from contextlib import contextmanager
import logging
import unittest

from .context import Context

log = logging.getLogger(__name__)


class EphemeralContextTestCase(unittest.TestCase):
  LOOPBACK = '127.0.0.1'
  
  def setUp(self):
    self.context = Context(ip=self.LOOPBACK)
    log.debug('XXX Starting context')
    self.context.start()

  def tearDown(self):
    log.debug('XXX Stopping context')
    self.context.stop()


@contextmanager
def ephemeral_context(**kw):
  context = Context(**kw)
  context.start()
  yield context
  context.stop()
