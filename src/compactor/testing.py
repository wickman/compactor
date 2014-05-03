from contextlib import contextmanager
import unittest

from .context import Context


class EphemeralContextTestCase(unittest.TestCase):
  def setUp(self):
    self.context = Context()
    self.context.start()

  def tearDown(self):
    self.context.stop()


@contextmanager
def ephemeral_context(**kw):
  context = Context(**kw)
  context.start()
  yield context
  context.stop()
