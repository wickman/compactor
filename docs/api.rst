compactor
=========

Global methods
--------------

Some methods are proxied to the global singleton Context in order to make
simple programs simpler to write.  These methods do the Right Thing™ for
most use-cases.

.. automodule:: compactor
    :members:
    :show-inheritance:

PIDs
----

.. code-block:: python

    from compactor.pid import PID
    pid = PID.from_string('slave(1)@192.168.33.2:5051')

.. autoclass:: compactor.pid.PID
    :members:

    .. automethod:: compactor.pid.PID.__init__


Processes
---------

.. code-block:: python

    from compactor.process import Process

    class PingProcess(Process):
      def initialize(self):
        super(PingProcess, self).initialize()
        self.pinged = threading.Event()

      @Process.install('ping')
      def ping(self, from_pid, body):
        self.pinged.set()

.. autoclass:: compactor.process.Process
    :members:

    .. automethod:: compactor.process.Process.__init__

.. autoclass:: compactor.process.ProtobufProcess
    :members:
    :show-inheritance:

Contexts
--------
.. code-block:: python

    from compactor.context import Context

    context = Context(ip='127.0.0.1', port=8081)
    context.start()

    ping_process = PingProcess('ping')
    ping_pid = context.spawn(ping_process)

    context.join()

.. autoclass:: compactor.context.Context
    :members:

    .. automethod:: compactor.context.Context.__init__