from flask import request
from functools import wraps
import random


LOG_REQUEST_RATE = 'log_request_rate'


def log_request_rate(sample_rate=1):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*fn_args, **fn_kwargs):
            if request:
                setattr(request, LOG_REQUEST_RATE, sample_rate)
            return fn(*fn_args, **fn_kwargs)
        return wrapper
    return decorator


def hit_log_request():
    if request:
        rate = getattr(request, LOG_REQUEST_RATE, 1)
        if rate == 0:
            return False
        elif rate == 1 or random.random() < rate:
            return True
        return False
    return True
