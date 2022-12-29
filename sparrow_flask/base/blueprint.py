# -*- coding: utf-8 -*-
import marshmallow as ma
from flask_smorest import Blueprint as _Blueprint
from sparrow_flask.base.scaffold import Scaffold


class Blueprint(_Blueprint, Scaffold):
    """Blueprint that registers info in API documentation"""

    def __init__(self, *args, **kwargs):
        """

        :param security_requirements: SecurityScheme, List[SecurityScheme],
            SecurityRequirement or List[SecurityRequirement]
        :param wishpost_oauth: tuple, (List[string], List[string])
        The first is required permissions, the second is required roles.
        """
        super().__init__(*args, **kwargs)

    def arguments(self, data_clz, *args, **kwargs):
        base_schema = kwargs.pop('base_schema', ma.Schema)
        schema = self._data_clz_to_schema(data_clz, base_schema=base_schema)
        return super().arguments(schema, *args, **kwargs)

    def response(
            self, status_code=200, data_clz=None, *, description=None,
            example=None, examples=None, headers=None, base_schema=ma.Schema
    ):
        """add response handling"""
        schema = self._data_clz_to_schema(data_clz, base_schema=base_schema)
        return super().response(status_code, schema=schema, description=description,
                                example=example, examples=examples, headers=headers)
