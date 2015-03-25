class PID(object):  # noqa
  __slots__ = ('ip', 'port', 'id')

  @classmethod
  def from_string(cls, pid):
    """Parse a PID from its string representation.

    PIDs may be represented as name@ip:port, e.g.

    .. code-block:: python

        pid = PID.from_string('master(1)@192.168.33.2:5051')

    :param pid: A string representation of a pid.
    :type pid: ``str``
    :return: The parsed pid.
    :rtype: :class:`PID`
    :raises: ``ValueError`` should the string not be of the correct syntax.
    """
    try:
      id_, ip_port = pid.split('@')
      ip, port = ip_port.split(':')
      port = int(port)
    except ValueError:
      raise ValueError('Invalid PID: %s' % pid)
    return cls(ip, port, id_)

  def __init__(self, ip, port, id_):
    """Construct a pid.

    :param ip: An IP address in string form.
    :type ip: ``str``
    :param port: The port of this pid.
    :type port: ``int``
    :param id_: The name of the process.
    :type id_: ``str``
    """
    self.ip = ip
    self.port = port
    self.id = id_

  def __hash__(self):
    return hash((self.ip, self.port, self.id))

  def __eq__(self, other):
    return isinstance(other, PID) and (
      self.ip == other.ip and
      self.port == other.port and
      self.id == other.id
    )

  def __ne__(self, other):
    return not (self == other)

  def as_url(self, endpoint=None):
    url = 'http://%s:%s/%s' % (self.ip, self.port, self.id)
    if endpoint:
      url += '/%s' % endpoint
    return url

  def __str__(self):
    return '%s@%s:%d' % (self.id, self.ip, self.port)

  def __repr__(self):
    return 'PID(%s, %d, %s)' % (self.ip, self.port, self.id)
