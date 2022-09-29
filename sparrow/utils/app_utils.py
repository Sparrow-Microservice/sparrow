from flask import request


def get_meth_from_view_func(view_func, to_assert=True):
    view_class = getattr(view_func, 'view_class', None)
    if view_class:
        meth = getattr(view_class, request.method.lower(), None)
        # If the request method is HEAD and we don't have a handler for it
        # retry with GET.
        if meth is None and request.method == "HEAD":
            meth = getattr(view_class, "get", None)
        if to_assert:
            assert meth is not None, "Unimplemented method %r" % request.method
        return meth
    return view_func
