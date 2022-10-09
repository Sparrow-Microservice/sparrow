import marshmallow as ma
import marshmallow_dataclass as mad
from sparrow.base.schema import WishSchema


def data_clz_to_schema(data_clz, base_schema=WishSchema):
    """
    Convert dataclass to schema
    """
    if issubclass(data_clz, ma.Schema) or isinstance(data_clz, ma.Schema):
        # data_clz is schema
        schema = data_clz
    else:
        # data_clz is object
        schema = mad.class_schema(data_clz, base_schema)
    return schema
