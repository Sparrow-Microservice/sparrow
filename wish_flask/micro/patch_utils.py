import functools
import inspect

from wish_flask.micro.micro_exceptions import MicroApiErrorException, MicroApiUnauthorizedException, \
    MicroApiValidationException
from wish_flask.exceptions.api_exception import StandaloneApiException, PropagateEnum, InternalApiException
from wish_flask.micro.utils import is_micro_api
from wish_flask.utils.convert_utils import json_decode
from wish_flask.exceptions.api_exception import ApiException as ServerApiException
from wish_flask.micro.exceptions import ApiException as ClientApiException
from wish_flask.monitor.metrics import METRIC_MICRO_CLIENT_API_ERROR_COUNT, \
    METRIC_MICRO_CLIENT_REQUEST_COUNT, METRIC_MICRO_CLIENT_REQUEST_TIME
import time


def convert_api_exception(ce):
    if ce.status == 400:  # Should be ServerApiException
        if ce.body:
            body_dict = None
            try:
                body_dict = json_decode(ce.body)
            except ValueError:
                pass
            if isinstance(body_dict, dict):
                code = body_dict.get('code', None)
                msg = body_dict.get('msg', None)
                data = body_dict.get('data', None)
                propagate = ce.headers.get('propagate') if ce.headers else None
                if code:
                    if propagate == PropagateEnum.INTERNAL and is_micro_api():
                        return InternalApiException(code, msg, data=data)
                    elif propagate == PropagateEnum.THROUGHOUT:
                        return ServerApiException(code, msg, data=data)
                    return StandaloneApiException(code, msg, data=data)
    elif ce.status == 403:
        return MicroApiUnauthorizedException(ce)
    elif ce.status == 422:
        return MicroApiValidationException(ce)
    elif ce.status == 599:
        return MicroApiErrorException(ce)
    return ce


# raise ServerApiException if possible
def server_exp_check(f, app_config, host):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        resource_path = args[1]
        method = args[2]
        METRIC_MICRO_CLIENT_REQUEST_COUNT.inc(1, **{'from': app_config.get('service_name', 'unknown'),
                                                    'to': host,
                                                    'env': app_config.get('env', 'unknown'),
                                                    'url': resource_path,
                                                    'method': method})
        start_at = time.time()
        try:
            return f(*args, **kwargs)
        except ClientApiException as ce:
            METRIC_MICRO_CLIENT_API_ERROR_COUNT.inc(1, **{'env': app_config.get('env', 'unknown'),
                                                          'url': resource_path,
                                                          'method': method,
                                                          'err_type': ce.status,
                                                          'from': app_config.get('service_name'),
                                                          'to': host})
            e = convert_api_exception(ce)
            if e != ce:
                raise e from None
            raise
        finally:
            end_at = time.time()
            METRIC_MICRO_CLIENT_REQUEST_TIME.observe(end_at - start_at, **{'env': app_config.get('env', 'unknown', ),
                                                                           'url': resource_path,
                                                                           'method': method,
                                                                           'from': app_config.get('service_name'),
                                                                           'to': host})

    return wrapper


# patch api client, e.g. ApiClient
def patch_client(client_kls, app_config, host):
    # Patch function call_api in client for trying to convert ServerApiException
    if hasattr(client_kls, 'call_api') and not getattr(client_kls, 'openapi_patched', None):
        client_kls.call_api = server_exp_check(client_kls.call_api, app_config, host)
        setattr(client_kls, 'openapi_patched', True)


# patch generated api method
def patch_api(api_fn):
    # currently do nothing
    return api_fn


def is_api_method(obj):
    return (inspect.isfunction(obj) or inspect.ismethod(obj)) and \
           not obj.__name__.startswith('__')


# patch generated api class, e.g. AuthApi
def patch_api_kls(api_kls):
    members = inspect.getmembers(api_kls, is_api_method)
    for name, member in members:
        setattr(api_kls, name, patch_api(member))
