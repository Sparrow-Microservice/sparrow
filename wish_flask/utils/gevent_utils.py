import socket
try:
    import psycopg2
except:
    psycopg2 = None

if psycopg2:
    from psycopg2 import extensions

try:
    from gevent.socket import wait_read, wait_write
except:
    wait_read = wait_write = None


_psycopg2_patched = False


def is_gevent_patched():
    try:
        from gevent import socket as gsocket
    except:
        gsocket = None
    if gsocket and socket.socket is gsocket.socket:
        return True
    return False


def patch_psycopg2():
    global _psycopg2_patched
    if not _psycopg2_patched and psycopg2:
        extensions.set_wait_callback(_gevent_wait_callback)
        _psycopg2_patched = True


def _gevent_wait_callback(conn, timeout=None):
    """A wait callback useful to allow gevent to work with Psycopg."""
    """https://www.psycopg.org/docs/advanced.html#support-for-coroutine-libraries"""
    """https://github.com/zacharyvoase/gevent-psycopg2/blob/master/lib/gevent_psycopg2.py"""

    while True:
        state = conn.poll()
        if state == extensions.POLL_OK:
            break
        elif state == extensions.POLL_READ:
            wait_read(conn.fileno(), timeout=timeout)
        elif state == extensions.POLL_WRITE:
            wait_write(conn.fileno(), timeout=timeout)
        else:
            raise psycopg2.OperationalError(
                "Bad result from poll: %r" % state)