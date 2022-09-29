from werkzeug.exceptions import Forbidden
import re
from flask import request

from wish_flask.base.view import ViewFilter
from wish_flask.micro.utils import is_micro_api
from wish_flask.security.security_requirement import SecurityRequirement
from wish_flask.utils.app_utils import get_meth_from_view_func


class SecurityCheckViewFilter(ViewFilter):
    def __init__(self, api, check_paths=None, exclude_paths=None):
        """

        :param api: WishApi instance
        :param check_paths: list of paths (regex) to check
        :param exclude_paths: list of paths (regex) to not check
        """
        super().__init__()
        self.api = api
        if check_paths and not isinstance(check_paths, (list, tuple)):
            check_paths = [check_paths]
        self.check_paths = check_paths
        if exclude_paths and not isinstance(exclude_paths, (list, tuple)):
            exclude_paths = [exclude_paths]
        self.exclude_paths = exclude_paths

    def get_security(self, meth_func):
        security = self.api.global_security_requirements
        if is_micro_api() and self.api.micro_security_requirements:
            security = self.api.micro_security_requirements
        security = getattr(meth_func, '_apidoc', {}).get('security', security)
        return security

    @property
    def security_exception(self):
        return Forbidden(description='Security validation failed')

    def need_check(self, meth):
        if self.exclude_paths:
            if any(re.match(ep, request.path) for ep in self.exclude_paths):
                return False
        if self.check_paths:
            if not any(re.match(cp, request.path) for cp in self.check_paths):
                return False
        if not getattr(meth, '_apidoc', {}).get('wish_api'):
            return False
        if getattr(meth, '_apidoc', {}).get('no_security'):
            return False
        return True

    def process(self, next_filter_node, view_func, fargs, fkwargs):
        meth = get_meth_from_view_func(view_func)
        if not self.need_check(meth):
            return self.process_next(next_filter_node, view_func, fargs, fkwargs)
        security = self.get_security(meth)
        if not SecurityRequirement.multi_check(security):
            raise self.security_exception
        return self.process_next(next_filter_node, view_func, fargs, fkwargs)
