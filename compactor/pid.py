
class PID(object):
  __slots__ = ('ip', 'port', 'id')

  @classmethod
  def from_string(cls, pid):
    try:
      id_, ip_port = pid.split('@')
      ip, port = ip_port.split(':')
      port = int(port)
    except ValueError:
      raise ValueError('Invalid PID: %s' % pid)
    return cls(ip, port, id_)

  def __init__(self, ip, port, id_):
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
