import unittest

from .context import Context


class EphemeralContextTestCase(unittest.TestCase):
  def setUp(self):
    self.context = Context()
    self.context.start()

  def tearDown(self):
    self.context.stop()

