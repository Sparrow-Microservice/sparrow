# -*- coding: utf-8 -*-
import marshmallow as ma
from flask_smorest import Blueprint
from sparrow.utils.dataclass_to_schema import data_clz_to_schema

from sparrow.base.schema import WishSchema


class WishBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def arguments(self, data_clz, *args, **kwargs):
        base_schema = kwargs.pop('base_schema', WishSchema)
        schema = data_clz_to_schema(data_clz, base_schema=base_schema)
        # ???
        kwargs.setdefault('unknown', ma.EXCLUDE)
        return super().arguments(schema, *args, **kwargs)

    def response(
            self, status_code=200, data_clz=None, *, description=None,
            example=None, examples=None, headers=None, base_schema=WishSchema
    ):
        schema = data_clz_to_schema(data_clz, base_schema=base_schema)
        return super().response(status_code, schema=schema, description=description,
                                example=example, examples=examples, headers=headers)
