
CRLF = b'\r\n'


def encode_request(from_pid, to_pid, method, body=None, content_type=None, legacy=False):
  """
  Encode a request into a raw HTTP request. This function returns a string
  of bytes that represent a valid HTTP/1.0 request, including any libprocess
  headers required for communication.

  Use the `legacy` option (set to True) to use the legacy User-Agent based
  libprocess identification.
  """

  if body is None:
    body = b''

  headers = [
    'POST /{process}/{method} HTTP/1.0'.format(process=to_pid.id, method=method),
    'Connection: Keep-Alive',
    'Content-Length: %d' % len(body)
  ]

  if legacy:
    headers.append('User-Agent: libprocess/{pid}'.format(pid=from_pid))
  else:
    headers.append('Libprocess-From: {pid}'.format(pid=from_pid))

  if content_type is not None:
    headers.append('Content-Type: {content_type}'.format(content_type=content_type))

  headers = [header.encode('utf8') for header in headers]

  def iter_fragments():
    for fragment in headers:
      yield fragment.encode('utf8')
      yield CRLF
    yield CRLF
    if body:
      yield body

  return b''.join(iter_fragments())
