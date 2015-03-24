=======
CHANGES
=======

-----
0.2.2
-----

* Fix the condition where multiple ``send``/``link`` calls to the same pid could race in
  ``Context.maybe_connect``.

* Fix the issue where Process HTTP routes were not bound until after ``initialize``.  This could
  result in races whereby you'd receive calls from remote processes before ``initialize`` exited,
  causing flaky behavior especially in tests.

-----
0.2.1
-----

* Restores local dispatch so that you do not need to install methods intended for local
  dispatching only.

* Fixes a race condition on ``Context.stop`` that could cause the event loop to raise an
  uncaught exception on teardown.

-----
0.2.0
-----

* Adds vagrant-based integration test to test compactor against reference libprocess.

* Fixes Python 3 support, pinning to protobof >= 2.6.1 < 2.7 which has correct support.

-----
0.1.3
-----

* ``Context.singleton()`` now calls ``Thread.start`` on construction.

* Pins compactor to ``tornado==4.1.dev1`` which forces you to use a
  master-built tornado distribution.

-----
0.1.2
-----

* Temporarily removes local dispatch so that local sending works with protobuf processes.

-----
0.1.1
-----

* Initial functioning release.
