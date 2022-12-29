import marshmallow_dataclass as mad
import marshmallow as ma


class Scaffold:
    """Common behavior shared between Sparrow and Blueprint
    """

    @classmethod
    def _data_clz_to_schema(cls, data_clz, base_schema=ma.Schema):
        if issubclass(data_clz, ma.Schema) or isinstance(data_clz, ma.Schema):
            # data_clz is schema
            schema = data_clz
        else:
            # data_clz is object
            schema = mad.class_schema(data_clz, base_schema)
        return schema
