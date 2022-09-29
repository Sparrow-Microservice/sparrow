from flask import request

from sparrow.micro.constants import MICRO_API_FLAG


def is_micro_api():
    if request:
        return getattr(request, MICRO_API_FLAG, False)
    return False
