CRLF = b'\r\n'


def encode_request(
    from_process,
    to_process,
    method,
    body=None,
    content_type=None,
    legacy=False):  # set legacy=True if we should use User-Agent based identification

  body = body or b''

  headers = [
      'POST /{process}/{method} HTTP/1.0'.format(process=to_process.id, method=method),
      'Connection: Keep-Alive',
  ]

  if legacy:
    headers.append('User-Agent: libprocess/{pid}'.format(pid=from_process))
  else:
    headers.append('Libprocess-From: {pid}'.format(pid=from_process))

  if content_type is not None:
    headers.append('Content-Type: {content_type}'.format(content_type=content_type))

  headers.append('Content-Length: {length}'.format(length=len(body)))

  headers = [header.encode('utf8') for header in headers]

  def iter_fragments():
    for fragment in headers:
      yield fragment.encode('utf8')
      yield CRLF
    yield CRLF
    if body:
      yield body

  return b''.join(iter_fragments())
