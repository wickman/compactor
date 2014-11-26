from compactor.http import (
    Header,
    Headers,
    crlf_split,
    crlf_tokenize,
    Request,
)

import pytest


def test_crlf_tokenize():
  tok = crlf_split

  assert list(tok(b'')) == [b'']
  assert list(tok(b'\r')) == [b'\r']
  assert list(tok(b'\n')) == [b'', b'']
  assert list(tok(b'\r\n')) == [b'', b'']
  assert list(tok(b'a\nb\r\nc\rd\r\n')) == [b'a', b'b', b'c\rd', b'']


def test_header_canonicalization():
  assert Header.canonicalize_name(b'') == b''
  assert Header.canonicalize_name(b'a') == b'A'
  assert Header.canonicalize_name(b'abc') == b'Abc'
  assert Header.canonicalize_name(b'a-b') == b'A-B'
  assert Header.canonicalize_name(b'content-type') == b'Content-Type'


def test_headers():
  stream = b'\n'.join([
      b'Host:   eXaMpLe.com',
      b'Content-type:\ttext/html',
  ])
  read_bytes, headers = Headers.from_bytes(stream)
  assert read_bytes == len(stream)
  assert headers[b'host'] == 'eXaMpLe.com'
  assert headers[b'content-type'] == 'text/html'


def test_response_parsing():
  stream_elements = [
      b'GET / HTTP/1.1',
      b'User-agent: Zaphod Beeblebrox',
      b''
  ]

  print('%r' % b'\r\n'.join(stream_elements))
  with pytest.raises(Request.ParseError):
    request = Request.from_bytes(b'\r\n'.join(stream_elements))

  stream_elements.append(b'')
  print('%r' % b'\r\n'.join(stream_elements))
  request = Request.from_bytes(b'\r\n'.join(stream_elements))
  assert request.method == b'GET'
  assert request.uri == b'/'
  assert request.headers[b'User-Agent'] == b'Zaphod Beeblebrox'
  assert len(request.headers) == 1
  assert request.body == b''
  assert request.version == b'HTTP/1.1'

