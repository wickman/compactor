=======
CHANGES
=======

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
