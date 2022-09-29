from flask import request

from sparrow.base.view import ViewFilter
from sparrow.micro.constants import MICRO_API_FLAG
from sparrow.utils.app_utils import get_meth_from_view_func


class MicroViewFilter(ViewFilter):
    def process(self, next_filter_node, view_func, fargs, fkwargs):
        meth = get_meth_from_view_func(view_func)
        micro = getattr(meth, '_apidoc', {}).get('micro')
        if request and micro:
            setattr(request, MICRO_API_FLAG, micro)
        return self.process_next(next_filter_node, view_func, fargs, fkwargs)