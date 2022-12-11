# -*- coding: utf-8 -*-
import typing as t

from .wrappers import Response, Request
from . import typing as ft
from .globals import request_ctx, request
from .ctx import AppContext, RequestContext

from werkzeug.exceptions import HTTPException, InternalServerError
from werkzeug.wrappers import Response as BaseResponse
from werkzeug.routing import Rule, Map, MapAdapter


class Sparrow(object):
    request_class = Request
    response_class = Response
    url_rule_class = Rule
    url_map_class = Map

    def __init__(self, config):
        self.config = config
        self.view_functions: t.Dict[str, t.Callable] = {}
        self.url_map = self.url_map_class()

    def __call__(self, environ: dict, start_response: t.Callable) -> t.Any:
        """The WSGI server calls the Flask application object as the
        WSGI application. This calls :meth:`wsgi_app`, which can be
        wrapped to apply middleware.
        :param environ: A WSGI environment.
        :param start_response: A callable accepting a status code,
            a list of headers, and an optional exception context to
            start the response.
        """
        return self.wsgi_app(environ, start_response)

    def _endpoint_from_view_func(self, view_func: t.Callable) -> str:
        """Internal helper that returns the default endpoint for a given
        function.  This always is the function name.
        """
        assert view_func is not None, "expected view func if endpoint is not provided."
        return view_func.__name__

    def create_url_adapter(self, request: t.Optional[Request]) -> t.Optional[MapAdapter]:
        return self.url_map.bind_to_environ(request.environ)

    def request_context(self, environ: dict) -> RequestContext:
        return RequestContext(self, environ)

    def route(self, rule: str, **options: t.Any) -> t.Callable[[ft.T_route], ft.T_route]:
        def decorator(f: ft.T_route) -> ft.T_route:
            endpoint = options.pop("endpoint", None)
            self.add_url_rule(rule, endpoint, f, **options)
            return f

        return decorator

    def add_url_rule(
            self,
            rule: str,
            endpoint: t.Optional[str] = None,
            view_func: t.Optional[ft.RouteCallable] = None,
            **options: t.Any,
    ) -> None:
        """Connects a URL rule.  Works exactly like the :meth:`route`
            decorator.  If a view_func is provided it will be registered with the
            endpoint.
        """
        if endpoint is None:
            endpoint = self._endpoint_from_view_func(view_func)

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
        rule = req.url_rule
        view_args: t.Dict[str, t.Any] = req.view_args

        return self.view_functions[rule.endpoint](**view_args)

    def make_response(self, rv: ft.ResponseReturnValue) -> Response:
        if isinstance(rv, tuple):
            rv, status, headers = rv
            rv = self.response_class(
                rv,
                status=status,
                headers=headers,  # type: ignore[arg-type]
            )
            return rv
        elif isinstance(rv, BaseResponse) or callable(rv):
            rv = self.response_class.force_type(
                rv, request.environ  # type: ignore[arg-type]
            )
            return rv
        else:
            raise TypeError(
                "The view function did not return a valid"
                " response. The return type must be a string,"
                " dict, list, tuple with headers or status,"
                " Response instance, or WSGI callable, but it was a"
                f" {type(rv).__name__}."
            )

    def finalize_request(
            self,
            rv: t.Union[ft.ResponseReturnValue, HTTPException],
    ) -> Response:
        response = self.make_response(rv)
        return response

    def full_dispatch_request(self) -> Response:
        try:
            rv = self.dispatch_request()
            return self.finalize_request(rv)
        except Exception as e:
            raise e

    def handle_exception(self, e: Exception) -> Response:
        server_error = InternalServerError(original_exception=e)
        return self.finalize_request(server_error)

    def app_context(self) -> AppContext:
        return AppContext(self)

    def wsgi_app(self, environ: dict, start_response: t.Callable) -> t.Any:
        ctx = self.request_context(environ)
        error: t.Optional[BaseException] = None
        try:
            try:
                ctx.push()
                response = self.full_dispatch_request()
            except Exception as e:
                error = e
                response = self.handle_exception(e)
            return response(environ, start_response)
        finally:
            ctx.pop(error)

    def run(self, host=None, port=None, debug=None, **options):
        from werkzeug.serving import run_simple
        if host is None:
            host = '127.0.0.1'
        if port is None:
            port = 5000
        run_simple(host, port, self, **options)
