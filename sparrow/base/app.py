# -*- coding: utf-8 -*-
import typing as t
from sparrow.base.ctx import RequestContext
from sparrow.base.wrappers import Response
import sys
from . import typing as ft
from werkzeug.exceptions import HTTPException
from werkzeug.datastructures import Headers
from collections.abc import Iterator as _abc_Iterator
from .json.provider import JSONProvider, DefaultJSONProvider
from werkzeug.wrappers import Response as BaseResponse
from werkzeug.routing import Rule, Map
from .globals import request_ctx

T_route = t.TypeVar("T_route", bound=ft.RouteCallable)


def _endpoint_from_view_func(view_func: t.Callable) -> str:
    """Internal helper that returns the default endpoint for a given
    function.  This always is the function name.
    """
    assert view_func is not None, "expected view func if endpoint is not provided."
    return view_func.__name__


class Sparrow(object):
    response_class = Response
    json_provider_class: t.Type[JSONProvider] = DefaultJSONProvider
    url_rule_class = Rule
    url_map_class = Map

    def __init__(self, config):
        self.config = config

        self.json: JSONProvider = self.json_provider_class(self)
        self.view_functions: t.Dict[str, t.Callable] = {}
        self.url_map = self.url_map_class()

    def __call__(self, environ: dict, start_response: t.Callable) -> t.Any:
        """The WSGI server calls the Flask application object as the
        WSGI application. This calls :meth:`wsgi_app`, which can be
        wrapped to apply middleware.
        """
        return self.wsgi_app(environ, start_response)

    def request_context(self, environ: dict) -> RequestContext:
        return RequestContext(self, environ)

    def route(self, rule: str, **options: t.Any) -> t.Callable[[T_route], T_route]:
        def decorator(f: T_route) -> T_route:
            endpoint = options.pop("endpoint", None)
            self.add_url_rule(rule, endpoint, f, **options)
            return f
        return decorator

    def add_url_rule(self, rule, endpoint, view_func, **options):
        """Connects a URL rule.  Works exactly like the :meth:`route`
            decorator.  If a view_func is provided it will be registered with the
            endpoint.
        """
        if endpoint is None:
            endpoint = _endpoint_from_view_func(view_func)

        options['endpoint'] = endpoint
        methods = options.pop('methods', None)

        # if the methods are not given and the view_func object knows its
        # methods we can use that instead.  If neither exists, we go with
        # a tuple of only ``GET`` as default.
        if methods is None:
            methods = getattr(view_func, "methods", None) or ("GET",)

        if isinstance(methods, str):
            raise TypeError(
                "Allowed methods must be a list of strings, for"
                ' example: @app.route(..., methods=["POST"])'
            )
        methods = {item.upper() for item in methods}

        rule = self.url_rule_class(rule, methods=methods, **options)

        self.url_map.add(rule)
        if view_func is not None:
            old_func = self.view_functions.get(endpoint)
            if old_func is not None and old_func != view_func:
                raise AssertionError(
                    "View function mapping is overwriting an existing"
                    f" endpoint function: {endpoint}"
                )
            self.view_functions[endpoint] = view_func

    def dispatch_request(self) -> ft.ResponseReturnValue:
        req = request_ctx.request
        # if req.routing_exception is not None:
        #     raise Exception(req.routing_exception)
        rule = req.url_rule
        view_args: t.Dict[str, t.Any] = req.view_args

        return self.view_functions[rule.endpoint](**view_args)

    def make_response(self, rv: ft.ResponseReturnValue) -> Response:
        status = headers = None
        # unpack tuple returns
        if isinstance(rv, tuple):
            len_rv = len(rv)

            # a 3-tuple is unpacked directly
            if len_rv == 3:
                rv, status, headers = rv  # type: ignore[misc]
            # decide if a 2-tuple has status or headers
            elif len_rv == 2:
                if isinstance(rv[1], (Headers, dict, tuple, list)):
                    rv, headers = rv
                else:
                    rv, status = rv  # type: ignore[assignment,misc]
            # other sized tuples are not allowed
            else:
                raise TypeError(
                    "The view function did not return a valid response tuple."
                    " The tuple must have the form (body, status, headers),"
                    " (body, status), or (body, headers)."
                )

        # the body must not be None
        if rv is None:
            raise Exception("The view function did not return a valid response")
            # raise TypeError(
            #     f"The view function for {request.endpoint!r} did not"
            #     " return a valid response. The function either returned"
            #     " None or ended without a return statement."
            # )

        # make sure the body is an instance of the response class
        if not isinstance(rv, self.response_class):
            if isinstance(rv, (str, bytes, bytearray)) or isinstance(rv, _abc_Iterator):
                # let the response class set the status and headers instead of
                # waiting to do it manually, so that the class can handle any
                # special logic
                rv = self.response_class(
                    rv,
                    status=status,
                    headers=headers,  # type: ignore[arg-type]
                )
                status = headers = None
            elif isinstance(rv, (dict, list)):
                rv = self.json.response(rv)
            elif isinstance(rv, BaseResponse) or callable(rv):
                # evaluate a WSGI callable, or coerce a different response
                # class to the correct type
                try:
                    rv = self.response_class.force_type(
                        rv, request.environ  # type: ignore[arg-type]
                    )
                except TypeError as e:
                    raise TypeError(
                        f"{e}\nThe view function did not return a valid"
                        " response. The return type must be a string,"
                        " dict, list, tuple with headers or status,"
                        " Response instance, or WSGI callable, but it"
                        f" was a {type(rv).__name__}."
                    ).with_traceback(sys.exc_info()[2]) from None
            else:
                raise TypeError(
                    "The view function did not return a valid"
                    " response. The return type must be a string,"
                    " dict, list, tuple with headers or status,"
                    " Response instance, or WSGI callable, but it was a"
                    f" {type(rv).__name__}."
                )

            rv = t.cast(Response, rv)
            # prefer the status if it was provided
            if status is not None:
                if isinstance(status, (str, bytes, bytearray)):
                    rv.status = status
                else:
                    rv.status_code = status

            # extend existing headers with provided headers
            if headers:
                rv.headers.update(headers)  # type: ignore[arg-type]

            return rv

    def finalize_request(
            self,
            rv: t.Union[ft.ResponseReturnValue, HTTPException],
            from_error_handler: bool = False,
    ) -> Response:
        response = self.make_response(rv)
        return response

    def full_dispatch_request(self) -> Response:
        try:
            rv = self.dispatch_request()
        except Exception as e:
            raise e
        return self.finalize_request(rv)

    def handle_exception(self, exec):
        pass

    def wsgi_app(self, environ: dict, start_response: t.Callable) -> t.Any:

        """ The actual WSGI application. This is not implemented in
        :meth:`__call__` so that middlewares can be applied without
        losing a reference to the app object. Instead of doing this::

            app = MyMiddleware(app)

        It's a better idea to do this instead::

            app.wsgi_app = MyMiddleware(app.wsgi_app)

        Then you still have the original application object around and
        can continue to call methods on it.
        :param environ: A WSGI environment.
        :param start_response: A callable accepting a status code,
            a list of headers, and an optional exception context to
            start the response.
        """
        ctx = self.request_context(environ)
        error: t.Optional[BaseException] = None
        try:
            try:
                ctx.push()
                response = self.full_dispatch_request()
            except Exception as e:
                error = e
                response = self.handle_exception(e)
            except:
                error = sys.exc_info()[1]
                raise
            return response(environ, start_response)
        finally:
            ctx.pop(error)

    def run(self, host=None, port=None, debug=None, **options):
        from werkzeug.serving import run_simple
        if host is None:
            host = '127.0.0.1'
        if port is None:
            server_name = self.config['SERVER_NAME']
            if server_name and ':' in server_name:
                port = int(server_name.rsplit(':', 1)[1])
            else:
                port = 5000

        run_simple(host, port, self, **options)
