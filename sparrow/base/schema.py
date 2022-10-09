import marshmallow as ma
from apispec.ext.marshmallow import resolve_schema_instance,  make_schema_key
from marshmallow import fields




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


class RspSchema(ma.Schema):

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
