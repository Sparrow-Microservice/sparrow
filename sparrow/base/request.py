import requests
from requests import Session, Request, Response
from requests.adapters import HTTPAdapter
from werkzeug.http import HTTP_STATUS_CODES

from sparrow.context.request_id_context import REQUEST_TRACING_ID_HEADERS, RequestTracingIdContext, REQUEST_ID_CLIENT_HEADERS
from sparrow.context.session_context import SESSION_SIGN_HEADERS, SessionSignContext
from sparrow.context.user_id_context import USER_ID_HEADERS, EncryptedUserIdContext


class EasyHttpAdapter(HTTPAdapter):
    def generate_response(self, status, reason='', request=None):
        response = Response()
        response.status_code = status
        response.reason = HTTP_STATUS_CODES.get(status, reason)
        if request:
            if isinstance(request.url, bytes):
                response.url = request.url.decode('utf-8')
            else:
                response.url = request.url
            response.request = request
        response.connection = self
        return response

    def send(self, request, **kwargs):
        raise_error = kwargs.pop('raise_error', True)
        try:
            return super().send(request, **kwargs)
        except Exception as e:
            if raise_error:
                raise
            return self.generate_response(599, reason=repr(e), request=request)


class EasySession(Session):
    def request(self, method, url,
                params=None, data=None, headers=None, cookies=None, files=None,
                auth=None, timeout=None, allow_redirects=True, proxies=None,
                hooks=None, stream=None, verify=None, cert=None, json=None,
                raise_error=True):
        # Copied from super.request for adding raise_error.
        req = Request(
            method=method.upper(),
            url=url,
            headers=headers,
            files=files,
            data=data or {},
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )
        prep = self.prepare_request(req)
        proxies = proxies or {}
        settings = self.merge_environment_settings(
            prep.url, proxies, stream, verify, cert
        )
        send_kwargs = {
            'timeout': timeout,
            'allow_redirects': allow_redirects,
            'raise_error': raise_error
        }
        send_kwargs.update(settings)
        resp = self.send(prep, **send_kwargs)
        return resp


class EasyRequestApiError(Exception):
    pass


class EasyRequest(object):
    # TODO Use pycurl-requests may be faster

    _session = None
    max_pool_size = 100
    service_name = 'unknown'
    max_connections_per_pool = 100
    SUPPORTED_METHODS = ["GET", "HEAD", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
    SUPPORTED_METHODS = SUPPORTED_METHODS + [m.lower() for m in SUPPORTED_METHODS]

    @classmethod
    def init(cls, app):
        cls._load_config(app=app)
        if EasyRequest._session:
            cls._get_session(recreate=True)

    @classmethod
    def request(cls, method, url, **kwargs):
        """Sends http method to URL.

        :param method: http method
        :param url: URL to request
        :param url_params: (Backward compatibility, Deprecated) (optional) Dictionary.
            url encode the param and add to the url.
        :param params: (optional) Dictionary, list of tuples or bytes to send.
            in the query string for the :class:`Request`.
        :param body: (Backward compatibility, Deprecated) (optional) bytes.
            raw data to send
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json data to send in the body of the :class:`Request`.
        :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param connect_timeout: (Backward compatibility, Deprecated) (optional)
            how long to wait on connect before giving up
        :param request_timeout: (Backward compatibility, Deprecated) (optional)
            how long to wait on request before giving up
        :param timeout: (optional) How many seconds to wait for the server to send data
            before giving up, as a float, or a :ref:`(connect timeout, read
            timeout) <timeouts>` tuple.
            (Default: 20.0)
        :param raise_error: (optional) Rethrow http errors. Default is True.
        :param allow_redirects: (optional) Boolean.
            Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection. Defaults to ``True``.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``.
        :param stream: (optional) if ``False``, the response content will be immediately downloaded.
        :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair.

        :return: :class:`Response <Response>` object
        :rtype: requests.Response
        """
        if method not in cls.SUPPORTED_METHODS:
            raise EasyRequestApiError(f"Invalid http verb {method}")
        cls._prepare_args(kwargs)

        return cls._get_session().request(method, url, **kwargs)

    @classmethod
    def _load_config(cls, app=None):
        if app:
            config = app.config.get('easy_request', {})
            cls.max_pool_size = config.get('max_pool_size', cls.max_pool_size)
            cls.max_connections_per_pool = config.get('max_connections_per_pool', cls.max_connections_per_pool)
            cls.service_name = app.config.get("service_name")

    @classmethod
    def _get_session(cls, recreate=False, app=None):
        # Use EasyRequest._session instead of cls._session to ensure one instance.
        if EasyRequest._session and recreate:
            EasyRequest._session.close()
        if not EasyRequest._session or recreate:
            cls._load_config(app=app)
            EasyRequest._session = EasySession()
            EasyRequest._session.mount(
                'https://',
                EasyHttpAdapter(
                    pool_connections=cls.max_pool_size,
                    pool_maxsize=cls.max_connections_per_pool
                )
            )
            EasyRequest._session.mount(
                'http://',
                EasyHttpAdapter(
                    pool_connections=cls.max_pool_size,
                    pool_maxsize=cls.max_connections_per_pool
                )
            )
        return EasyRequest._session

    @classmethod
    def _prepare_args(cls, kwargs):
        # Backward compatibility:
        # <connect_timeout>,<request_timeout>
        connect_timeout = kwargs.pop('connect_timeout', None)
        request_timeout = kwargs.pop('request_timeout', None)
        if connect_timeout or request_timeout:
            timeout = (connect_timeout or 20.0, request_timeout or 20.0)
        else:
            timeout = kwargs.get('timeout') or 20.0
        kwargs['timeout'] = timeout
        # <url_params>
        url_params = kwargs.pop('url_params', None)
        if url_params:
            kwargs['params'] = url_params
        # <body>
        body = kwargs.pop('body', None)
        if body:
            kwargs['data'] = body

        headers = kwargs.setdefault('headers', {})
        cls._prepare_contexts(headers)

    @classmethod
    def _prepare_contexts(cls, headers):
        def add_context_header(key, value):
            if value:
                headers[key] = value

        add_context_header(REQUEST_TRACING_ID_HEADERS[0], RequestTracingIdContext.get())
        add_context_header(SESSION_SIGN_HEADERS[0], SessionSignContext.get())
        add_context_header(USER_ID_HEADERS[0], EncryptedUserIdContext.get())
        # send request with client service name
        add_context_header(REQUEST_ID_CLIENT_HEADERS[0], cls.service_name)
