from collections import MutableMapping


def crlf_tokenize(stream, start=0):
  while True:
    end = stream.find(b'\n', start)
    if end == -1:
      yield slice(start, len(stream)), None
      return
    elif end == 0:
      yield slice(start, end), end + 1
    elif stream[end - 1] == b'\r':
      yield slice(start, end - 1), end + 1
    else:
      yield slice(start, end), end + 1
    start = end + 1
    continue


def crlf_split(stream):
  for slice_, _ in crlf_tokenize(stream):
    yield stream[slice_]


class Header(object):
  __slots__ = ('name', 'value')

  @classmethod
  def canonicalize_name(cls, name):
    return b'-'.join(fragment.capitalize() for fragment in name.split(b'-'))

  @classmethod
  def from_bytes(cls, stream):
    split_stream = stream.split(':', 1)
    if len(split_stream) == 1:
      raise ValueError('Invalid header: %r' % stream)
    name, value = split_stream
    return cls(name, value.lstrip())

  def __init__(self, name, value):
    self.name = self.canonicalize_name(name)
    self.value = value


class Headers(MutableMapping):
  @classmethod
  def from_bytes(cls, stream):
    """Given a stream of bytes, return the Headers object and the number of bytes consumed."""
    headers = cls()

    consecutive_lfs = 0
    for slice_, next_start in crlf_tokenize(stream):
      if slice_.start - slice_.stop == 0:
        consecutive_lfs += 1
        if consecutive_lfs == 2:
          return next_start, headers
      else:
        consecutive_lfs = 0
        headers.add(Header.from_bytes(stream[slice_]))

    raise ValueError('Incomplete headers (insufficient CRLFs.)')

  def __init__(self):
    self.__d = {}

  def add(self, header):
    self[header.name] = header.value

  def __getitem__(self, name):
    return self.__d[Header.canonicalize_name(name)]

  def __setitem__(self, name, value):
    self.__d[Header.canonicalize_name(name)] = value

  def __delitem__(self, name):
    del self.__d[Header.canonicalize_name(name)]

  def __iter__(self):
    return iter(self.__d)

  def __len__(self):
    return len(self.__d)


class Request(object):
  class Error(Exception): pass
  class ParseError(ValueError, Error): pass

  __slots__ = ('method', 'uri', 'headers', 'body', 'version')

  @classmethod
  def from_bytes(cls, stream):
    stream_tokenizer = crlf_tokenize(stream)
    slice_, next_start = next(stream_tokenizer)
    method, uri, version = cls.parse_first_line(stream[slice_])
    try:
      next_next_start, headers = Headers.from_bytes(stream[next_start:])
    except ValueError as e:
      raise cls.ParseError('Malformed headers: %s' % e)
    return cls(
        method,
        uri,
        headers,
        body=b'' if next_next_start is None else stream[next_start + next_next_start:],
        version=version)

  @classmethod
  def parse_first_line(cls, first_line):
    try:
      method, uri, version = first_line.split()
    except ValueError:
      raise cls.ParseError('Malformed request: %r' % first_line)
    return method, uri, version

  def __init__(self,
               method,
               uri,
               headers,
               body=b'',
               version='HTTP/1.1'):
    self.method = method  # TODO sanitize
    self.uri = uri  # TODO sanitize
    self.headers = headers
    self.body = body
    self.version = version  # TODO sanitize


class Response(object):
  def encode(self):
    pass
