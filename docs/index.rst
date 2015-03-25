.. compactor documentation master file, created by
   sphinx-quickstart on Tue Mar 24 15:27:46 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

compactor
=========
.. image:: https://travis-ci.org/wickman/compactor.svg?branch=master
    :target: https://travis-ci.org/wickman/compactor

compactor is a pure python implementation of libprocess, the actor library
underpinning `mesos <https://mesos.apache.org>`_.

.. toctree::
   :maxdepth: 2

   api

getting started
===============

implementing a process is a matter of subclassing ``compactor.Process``.
you can "install" methods on processes using the ``install`` decorator.
this makes them remotely callable.

.. code-block:: python

    import threading

    from compactor import install, spawn, Process

    class PingProcess(Process):
      def initialize(self):
        self.pinged = threading.Event()

      @install('ping')
      def ping(self, from_pid, body):
        self.pinged.set()

    # construct the process
    ping_process = PingProcess('ping_process')

    # spawn the process, binding it to the current global context
    spawn(ping_process)

    # send a message to the process
    client = Process('client')
    spawn(client)
    client.send(ping_process.pid, 'ping')

    # ensure the message was delivered
    ping_process.pinged.wait()

each context is, in essence, a listening (ip, port) pair.

by default there is a global, singleton context.  use ``compactor.spawn`` to
spawn a process on it.  by default it will bind to ``0.0.0.0`` on an
arbitrary port.  this can be overridden using the ``LIBPROCESS_IP`` and
``LIBPROCESS_PORT`` environment variables.

alternately, you can create an instance of a ``compactor.Context``,
explicitly passing it ``port=`` and ``ip=`` keywords.  you can then call the
``spawn`` method on it to bind processes.

spawning a process does two things: it binds the process to the context,
creating a pid, and initializes the process.  the pid is a unique identifier
used for routing purposes.  in practice, it consists of an (ip, port, name)
tuple, where the ip and port are those of the context, and the name is the
name of the process.

when a process is spawned, its ``initialize`` method is called.  this can be
used to initialize state or initiate connections to other services, as
illustrated in the following example.

leader/follower pattern
=======================

.. code-block:: python

    import threading
    import uuid
    from compactor import install
    from compactor.process import Process

    class Leader(Process):
      def __init__(self):
        super(Leader, self).__init__('leader')
        self.followers = set()

      @install('register')
      def register(self, from_pid, uuid):
        self.send(from_pid, 'registered', uuid)

    class Follower(Process):
      def __init__(self, name, leader_pid):
        super(Follower, self).__init__(name)
        self.leader_pid = leader_pid
        self.uuid = uuid.uuid4().bytes
        self.registered = threading.Event()

      def initialize(self):
        super(Follower, self).initialize()
        self.send(self.leader_pid, 'register', self.uuid)

      def exited(self, from_pid):
        self.registered.clear()

      @install('registered')
      def registered(self, from_pid, uuid):
        if uuid == self.uuid:
          self.link(from_pid)
          self.registered.set()

with this, you can create two separate contexts:

.. code-block:: python

    from compactor import Context

    leader_context = Context(port=5051)
    leader = Leader()
    leader_context.spawn(leader)

    # at this point, leader_context.pid is a unique identifier for this leader process
    # and can be disseminated via service discovery or passed explicitly to other services,
    # e.g. 'leader@192.168.33.2:5051'.  the follower can be spawned in the same process,
    # in a separate process, or on a separate machine.

    follower_context = Context()
    follower = Follower('follower1', leader_context.pid)
    follower_context.spawn(follower)

    follower.registered.wait()

this effectively initiates a handshake between the leader and follower processes, a common
pattern building distributed systems using the actor model.

the ``link`` method links the two processes together.  should the connection be severed,
the ``exited`` method on the process will be called.

protocol buffer processes
=========================

mesos uses protocol buffers over the wire to support RPC.  compactor supports this natively.
simply subclass ``ProtobufProcess`` instead and use ``ProtobufProcess.install``

.. code-block:: python

    from compactor.process import ProtobufProcess
    from service_pb2 import ServiceRequestMessage, ServiceResponseMessage

    class Service(ProtobufProcess):
      @ProtobufProcess.install(ServiceRequestMessage)
      def request(self, from_pid, message):
        # message is a deserialized protobuf ServiceRequestMessage
        response = ServiceResponseMessage(...)
        # self.send automatically serializes the response, a protocol buffer, over the wire.
        self.send(from_pid, response)
