from gevent import monkey, getcurrent
monkey.patch_all()
from sparrow.utils.gevent_utils import patch_psycopg2
patch_psycopg2()
from gevent.pywsgi import WSGIServer, WSGIHandler
from gevent.signal import signal as gsignal

from flask import Flask
import argparse
import importlib
import signal
import time
import logging
from functools import partial

READ_REQUEST_START = 'READ_REQUEST_START'

# On prod, we use gevent WSGIServer to have only one process running in one k8s pod.
# If we use Gunicorn or uWSGI, we will have at least two processes in each pod, one is master and one is worker.


class GeventWSGIHandler(WSGIHandler):
    def read_requestline(self):
        t = time.time()
        setattr(getcurrent(), READ_REQUEST_START, t)
        try:
            return super().read_requestline()
        finally:
            delattr(getcurrent(), READ_REQUEST_START)


class GeventWSGIServer(WSGIServer):
    @classmethod
    def smart_join(cls, pool, timeout=None, read_timeout=None):
        limit = (time.time() + timeout) if timeout is not None else None
        while limit is None or time.time() < limit:
            greenlet_in_reading = 0
            for g in pool.greenlets:
                read_start_time = getattr(g, READ_REQUEST_START, None)
                if read_timeout is not None and read_start_time is not None:
                    greenlet_in_reading += read_start_time + read_timeout <= time.time()
            free_count = pool.free_count() + greenlet_in_reading
            if free_count != pool.size:
                time.sleep(0.1)
                continue
            break

    def stop(self, timeout=None):
        self.close()
        if timeout is None:
            timeout = self.stop_timeout
        read_timeout = getattr(self, 'stop_timeout_for_read', None)
        if self.pool:
            self.smart_join(self.pool, timeout=timeout, read_timeout=read_timeout)
            self.pool.kill(block=True, timeout=1)


class ServerRunner(object):
    def __init__(self, app_server, bind=None, stop_timeout=30, stop_timeout_for_read=2, pool_size=10000, auto_reload=False):
        self.app_server = app_server
        self.bind = bind
        self.stop_timeout = stop_timeout
        self.stop_timeout_for_read = stop_timeout_for_read
        self.pool_size = pool_size
        self.auto_reload = auto_reload

    def start_server(self):
        if self.auto_reload:
            from werkzeug.serving import run_with_reloader
            run_with_reloader(self._launch_server)
        else:
            self._launch_server()

    def _launch_server(self):
        app = self._load_app()
        app_auto_reload = app.config.get('auto_reload', False)
        run_fn = partial(self._run_server, app)
        if not self.auto_reload and app_auto_reload:
            self.auto_reload = app_auto_reload
            from werkzeug.serving import run_with_reloader
            run_with_reloader(run_fn)
        else:
            run_fn()

    def _load_app(self):
        module_name, app_name = self.app_server.split(':')
        module = importlib.import_module(module_name)
        app = getattr(module, app_name)
        return app

    def _run_server(self, app):
        if not self.bind:
            if isinstance(app, Flask):
                host = app.config.get('listener_host') or ''
                port = app.config.get('listener_port') or ''
                if host or port:
                    self.bind = host + ':' + str(port or '8080')
        if not self.bind:
            self.bind = ':8080'
        self._print_info()
        server = GeventWSGIServer(self.bind,
                                  app,
                                  spawn=self.pool_size,
                                  handler_class=GeventWSGIHandler,
                                  log=logging.getLogger('gevent_wsgi'),
                                  error_log=logging.getLogger('gevent_wsgi_error')
                                  )
        server.stop_timeout = self.stop_timeout
        # timeout for keepalive connections
        server.stop_timeout_for_read = self.stop_timeout_for_read

        def shutdown(*args):
            server.application.close()
            server._stop_event.set()

        # Gracefully shutdown for SIGTERM
        gsignal(signal.SIGTERM, shutdown)

        server.serve_forever()

    def _print_info(self):
        print("-------------------------------------")
        print("Starting server by gevent WSGIServer:")
        print('--bind: ', self.bind)
        print('--stop_timeout: ', self.stop_timeout)
        print('--stop_timeout_for_read: ', self.stop_timeout_for_read)
        print('--pool_size: ', self.pool_size)
        print('--auto_reload: ', self.auto_reload)
        print("-------------------------------------")


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("app", help="dotted name of WSGI app callable [module:callable]")
    parser.add_argument("-b", "--bind",
                        help="The socket to bind")
    parser.add_argument("-t", "--timeout",
                        help="Stop timeout", default=30)
    parser.add_argument("-r", "--timeout_read",
                        help="Stop timeout for reading request", default=2)
    parser.add_argument("-s", "--pool_size",
                        help="Pool size for greenlets", default=10000)
    parser.add_argument("-a", "--auto_reload", type=bool,
                        help="Auto reload if py files are changed", default=False)

    args = parser.parse_args()
    ServerRunner(
        args.app,
        bind=args.bind,
        stop_timeout=args.timeout,
        stop_timeout_for_read=args.timeout_read,
        pool_size=args.pool_size,
        auto_reload=args.auto_reload
    ).start_server()


if __name__ == '__main__':
    main()
