import uuid
from dataclasses import is_dataclass, MISSING
import marshmallow as ma
import decimal
from apispec.ext.marshmallow import resolve_schema_instance, resolve_schema_cls, make_schema_key

from wish_flask.base import fields
from wish_flask.utils.convert_utils import to_camel_case
from wish_flask.constent import SCHEMA_NAME_EXT


class WishSchema(ma.Schema):

    schema_name_ext = None

    def __init__(self, schema_name_ext=None, *args, **kwargs):
        """
        :param schema_name_ext: str
            The schema name extension used in doc (Openapi).
            It is only effective when schema modifiers are changed, e.g.
            "only", "exclude", "load_only", "dump_only", "partial"

        """
        super().__init__(*args, **kwargs)
        if schema_name_ext:
            self.schema_name_ext = schema_name_ext

    TYPE_MAPPING = {
        **ma.Schema.TYPE_MAPPING,
        str: fields.String,
        uuid.UUID: fields.UUID,
        decimal.Decimal: fields.Decimal,
    }

    @classmethod
    def get_schema_name(cls, data_schema):
        data_schema_clz = resolve_schema_cls(data_schema)
        data_schema_name = data_schema_clz.__name__
        if data_schema_name.endswith('Schema') or data_schema_name.endswith('Scheme'):
            data_schema_name = data_schema_name[:-6]
        if getattr(data_schema, SCHEMA_NAME_EXT, None):
            data_schema_name += to_camel_case(getattr(data_schema, SCHEMA_NAME_EXT), lower_rest=False)
        return data_schema_name

    # TODO from_dataclass may be cleaned as marshmallow_dataclass package is used.
    # Used for from_dataclass
    DATACLASS_TYPE_MAPPING = {
        **TYPE_MAPPING,
        list: fields.List
    }

    @classmethod
    def from_dataclass(cls, datacls):
        """Generate a Schema from a dataclass."""
        return cls.from_dict(
            {
                name: cls.make_field_for_type(dc_field.type, dc_field.default)
                for name, dc_field in datacls.__dataclass_fields__.items()
            },
            name=f"{datacls.__name__}Schema",
        )

    @classmethod
    def make_field_for_type(cls, type_, default=ma.missing):
        """Generate a marshmallow Field instance from a Python type."""
        if is_dataclass(type_):
            return fields.Nested(cls.from_dataclass(type_))
        # Get marshmallow field class for Python type
        origin_cls = getattr(type_, "__origin__", None) or type_
        FieldClass = cls.DATACLASS_TYPE_MAPPING[origin_cls]
        # Set `required` and `missing`
        required = default is MISSING
        field_kwargs = {"required": required}
        if not required:
            field_kwargs["missing"] = default
        # Handle list types
        if issubclass(FieldClass, fields.List):
            # Construct inner class
            args = getattr(type_, "__args__", [])
            if args:
                inner_type = args[0]
                inner_field = cls.make_field_for_type(inner_type)
            else:
                inner_field = fields.Field()
            field_kwargs["cls_or_instance"] = inner_field
        return FieldClass(**field_kwargs)


class RspSchemaCollector(object):
    collector = {}

    @classmethod
    def make_key(cls, data_schema):
        data_schema_inst = resolve_schema_instance(data_schema)
        data_schema_key = make_schema_key(data_schema_inst)
        many = data_schema_inst.many
        return data_schema_key, many

    @classmethod
    def get_schema(cls, key):
        return cls.collector.get(key)

    @classmethod
    def set_schema(cls, key, schema):
        cls.collector[key] = schema


class RspSchema(WishSchema):

    code = fields.Integer(metadata={"description": "Error code"})
    msg = fields.String(metadata={"description": "Error message"})
    data = fields.Dict(metadata={"description": "Api/Error data"})

    @classmethod
    def d(cls, data_schema):
        data_collector_key = RspSchemaCollector.make_key(data_schema)
        rsp_schema = RspSchemaCollector.get_schema(data_collector_key)
        if not rsp_schema:
            data_schema_name = cls.get_schema_name(data_schema)
            rsp_schema_name = [data_schema_name,
                               'List' if isinstance(data_schema, ma.Schema) and data_schema.many else '',
                               'RspSchema']
            rsp_schema_name = ''.join(rsp_schema_name)
            rsp_schema = cls.from_dict({'data': fields.Nested(data_schema)}, name=rsp_schema_name)
            RspSchemaCollector.set_schema(data_collector_key, rsp_schema)
        return rsp_schema


class Rsp(object):
    def __init__(self, code=0, msg='', data=None):
        self.code = code
        self.msg = msg
        self.data = data

    def to_dict(self):
        rt = {}

        def update(k, v):
            if v is not None:
                rt[k] = v
        update('code', self.code)
        update('msg', self.msg)
        update('data', self.data)
        return rt
