# -*- coding: utf-8 -*-
from functools import wraps
import marshmallow_dataclass as mad
import marshmallow as ma
from apispec.ext.marshmallow import resolve_schema_cls
from flask.views import MethodViewType
from flask_smorest import Blueprint
from flask_smorest.utils import unpack_tuple_response

from wish_flask.base.schema import WishSchema
from wish_flask.base.schema import RspSchema, Rsp
from wish_flask.security.security import SecurityScheme
from wish_flask.security.security_requirement import SecurityRequirement
from wish_flask.security.security_auth.wishpost_oauth_apikey import WishpostOauthAPIKey


class WishBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        """

        :param micro: bool. Used for micro apis.
        :param security_requirements: SecurityScheme, List[SecurityScheme],
            SecurityRequirement or List[SecurityRequirement]
        :param wishpost_oauth: tuple, (List[string], List[string])
        The first is required permissions, the second is required roles.
        """
        self.micro = kwargs.pop('micro', False)  # To indicate this is a bp for micro apis
        security_requirements = kwargs.pop('security_requirements', None)
        self.security_requirements = self.to_security_requirement_list(security_requirements)
        wishpost_oauth = kwargs.pop('wishpost_oauth', None)
        if wishpost_oauth:
            wishpost_oauth = self.to_security_requirement_list(WishpostOauthAPIKey(wishpost_oauth[0], wishpost_oauth[1]))
            if self.security_requirements:
                self.security_requirements.extend(wishpost_oauth)
            else:
                self.security_requirements = wishpost_oauth

        super().__init__(*args, **kwargs)
        self._prepare_doc_cbks.append(self._prepare_operation_id)
        self._prepare_doc_cbks.append(self._prepare_securities)

    @classmethod
    def to_security_requirement_list(cls, security_requirements):
        if security_requirements:
            if not isinstance(security_requirements, list):
                security_requirements = [security_requirements]
            if isinstance(security_requirements[0], SecurityScheme):
                security_requirements = [SecurityRequirement(*security_requirements)]
        return security_requirements

    def get_security_requirements(self):
        return self.security_requirements

    @classmethod
    def _data_clz_to_schema(cls, data_clz, base_schema=WishSchema):
        if issubclass(data_clz, ma.Schema) or isinstance(data_clz, ma.Schema):
            # data_clz is schema
            schema = data_clz
        else:
            # data_clz is object
            schema = mad.class_schema(data_clz, base_schema)
        return schema

    def arguments(self, data_clz, *args, **kwargs):
        base_schema = kwargs.pop('base_schema', WishSchema)
        schema = self._data_clz_to_schema(data_clz, base_schema=base_schema)
        kwargs.setdefault('unknown', ma.EXCLUDE)
        return super().arguments(schema, *args, **kwargs)

    def response(
            self, status_code=200, data_clz=None, *, description=None,
            example=None, examples=None, headers=None, base_schema=WishSchema
    ):
        schema = self._data_clz_to_schema(data_clz, base_schema=base_schema)
        return super().response(status_code, schema=schema, description=description,
                                example=example, examples=examples, headers=headers)

    def unified_rsp(
            self, status_code=200, data_clz=None, *, description=None,
            example=None, examples=None, headers=None, base_schema=WishSchema
    ):
        schema = self._data_clz_to_schema(data_clz, base_schema=base_schema)
        if schema:
            schema_clz = resolve_schema_cls(schema)
            if not issubclass(schema_clz, RspSchema):
                schema = RspSchema.d(schema)
        decorator = super().response(
            status_code, schema=schema,
            description=description, example=example, examples=examples, headers=headers
        )

        def unified_deco(func):
            @wraps(func)
            def unified_fun(*args, **kwargs):
                rt = func(*args, **kwargs)
                _rv, _status, _headers = unpack_tuple_response(rt)
                _rv = Rsp(data=_rv)
                return _rv, _status, _headers
            return decorator(unified_fun)
        return unified_deco

    def operation_id(self, operation_id):
        """Decorator to set operation id for view function.

        Operation id is used in Openapi Spec.
        """
        return self.doc(operationId=operation_id)

    def wishpost_oauth(self, require_permissions, require_roles):
        """Decorator to check user's permission and roles through session in request's cookie
        """
        security_requirements = [WishpostOauthAPIKey(require_permissions, require_roles)]
        return self.security(security_requirements=security_requirements)

    def security(self, security_requirements):
        """Decorator to set security requirements for view function.
        """
        security_requirements = self.to_security_requirement_list(security_requirements)

        def decorator(func):
            func._apidoc = getattr(func, '_apidoc', {})
            if 'security' in func._apidoc:
                func._apidoc['security'].extend(security_requirements)
            else:
                func._apidoc['security'] = security_requirements
            return func
        return decorator

    def micro_api(self):
        """Decorator to indicate that this is func for a micro api.
        """
        def decorator(func):
            func._apidoc = getattr(func, '_apidoc', {})
            func._apidoc['micro'] = True
            return func
        return decorator

    def no_security(self):
        """Decorator to indicate that this api needs no security check.
        """
        def decorator(func):
            func._apidoc = getattr(func, '_apidoc', {})
            func._apidoc['no_security'] = True
            return func
        return decorator

    def _store_func_docs(self, func, endpoint):
        func._apidoc = getattr(func, '_apidoc', {})
        if self.micro and func._apidoc.get('micro') is None:
            func._apidoc['micro'] = self.micro
        if self.security_requirements and not func._apidoc.get('security'):
            func._apidoc['security'] = self.security_requirements
        func._apidoc['endpoint'] = endpoint
        func._apidoc['wish_api'] = True  # Only wish apis are checked by security filter

    def _store_endpoint_docs(self, endpoint, obj, parameters, **options):
        if isinstance(obj, MethodViewType):
            for method in self.HTTP_METHODS:
                if method in obj.methods:
                    func = getattr(obj, method.lower())
                    self._store_func_docs(func, endpoint)
        else:
            self._store_func_docs(obj, endpoint)
        super()._store_endpoint_docs(endpoint, obj, parameters, **options)

    def _prepare_operation_id(self, doc, doc_info, *, method, **kwargs):
        operation_id = doc_info.get('manual_doc', {}).get('operationId')
        if not operation_id:
            endpoint = doc_info.get('endpoint')
            if endpoint:
                operation_id = endpoint + '.' + method
                doc['operationId'] = operation_id
        return doc

    def _prepare_securities(self, doc, doc_info, *, api, **kwargs):
        if doc_info.get('no_security'):
            doc['security'] = []
            return doc
        security = doc_info.get('security')
        from wish_flask.base.api import WishApi
        if isinstance(api, WishApi):
            if security:
                api.add_security_schema_from_requirements(security)
            else:
                if api.individual_global_security:
                    security = api.global_security_requirements
                if doc_info.get('micro') and api.micro_security_requirements:
                    security = api.micro_security_requirements
        if security:
            doc['security'] = SecurityRequirement.build_specs(security)
        return doc
