compactor
=========
.. image:: https://travis-ci.org/wickman/compactor.svg?branch=master
    :target: https://travis-ci.org/wickman/compactor

compactor is a pure python implementation of libprocess, the actor library
underpinning `mesos <https://mesos.apache.org>`_.


usage
=====

implementing a process is a matter of subclassing ``compactor.Process``.
you can "install" methods on processes using the ``install`` decorator.
this makes them remotely callable.

an example leader, follower pattern:

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

      @install('registered')
      def registered(self, from_pid, uuid):
        if uuid == self.uuid:
          self.link(from_pid)
          self.registered.set()


by default there is a global, singleton context.  use ``compactor.spawn`` to
spawn a process on it.  alternately, you can create an instance of a
``compactor.Context`` and call the ``spawn`` method on it.

spawning a process does two things: it creates a pid and initializes the
process.  the pid is a unique identifier used for routing purposes.  in
practice, it consists of an ``(ip, port, name)`` tuple.

when a process is spawned, its ``initialize`` method is called.  this can be
used to initialize state or initiate connections to other services, as
illustrated above in the leader/follower example.

.. code-block::

    import compactor

    leader = Leader()
    compactor.spawn(leader)

    follower = Follower('follower1', leader.pid)
    compactor.spawn(follower)

    follower.registered.wait()

this effectively initiates a handshake between the leader and follower processes.
