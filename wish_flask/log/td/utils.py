from typing import Any
import json


def _join_chars(chars):
    if not chars:
        return b''
    if isinstance(chars[0], bytes):
        return b''.join(chars)
    else:
        return ''.join(chars)


def merge_prefix(buf, size):
    """Replace the first entries in a deque of strings with a single
    string of up to size bytes.

    >>> import collections
    >>> d = collections.deque(['abc', 'de', 'fghi', 'j'])
    >>> merge_prefix(d, 5); print(d)
    deque(['abcde', 'fghi', 'j'])

    Strings will be split as necessary to reach the desired size.
    >>> merge_prefix(d, 7); print(d)
    deque(['abcdefg', 'hi', 'j'])

    >>> merge_prefix(d, 3); print(d)
    deque(['abc', 'defg', 'hi', 'j'])

    >>> merge_prefix(d, 100); print(d)
    deque(['abcdefghij'])

    taken from tornado.iostream
    """
    if len(buf) == 1 and len(buf[0]) <= size:
        return
    prefix = []
    remaining = size
    while buf and remaining > 0:
        chunk = buf.popleft()
        if len(chunk) > remaining:
            buf.appendleft(chunk[remaining:])
            chunk = chunk[:remaining]
        prefix.append(chunk)
        remaining -= len(chunk)
    buf.appendleft(_join_chars(prefix))


def json_encode(value: Any) -> str:
    """JSON-encodes the given Python object."""
    # Copied from tornado
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the JavaScript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    return json.dumps(value).replace("</", "<\\/")
