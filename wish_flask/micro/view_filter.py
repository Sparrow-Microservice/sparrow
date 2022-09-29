from flask import request

from wish_flask.base.view import ViewFilter
from wish_flask.micro.constants import MICRO_API_FLAG
from wish_flask.utils.app_utils import get_meth_from_view_func


class MicroViewFilter(ViewFilter):
    def process(self, next_filter_node, view_func, fargs, fkwargs):
        meth = get_meth_from_view_func(view_func)
        micro = getattr(meth, '_apidoc', {}).get('micro')
        if request and micro:
            setattr(request, MICRO_API_FLAG, micro)
        return self.process_next(next_filter_node, view_func, fargs, fkwargs)