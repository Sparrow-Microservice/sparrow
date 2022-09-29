from wish_flask.lib.py_enum import PyEnumMixin


class S3Type(PyEnumMixin):
    REAL = 'real'
    MOCK = 'mock'
    SAFE = 'safe'


class S3Registry(object):
    s3_mapping = {}  # Allow customization

    @classmethod
    def get_s3_clz(cls, s3_type):
        if s3_type == S3Type.REAL:
            from wish_flask.lib.s3.real_s3 import RealS3
            cls.s3_mapping[s3_type] = RealS3
            return RealS3
        elif s3_type == S3Type.MOCK:
            from wish_flask.lib.s3.mock_s3 import MockS3
            cls.s3_mapping[s3_type] = MockS3
            return MockS3
        elif s3_type == S3Type.SAFE:
            from wish_flask.lib.s3.safe_s3 import SafeS3
            cls.s3_mapping[s3_type] = SafeS3
            return SafeS3
        elif s3_type in S3Registry.s3_mapping:
            return S3Registry.s3_mapping[s3_type]
        return None


class S3Factory(object):
    @classmethod
    def make_s3(cls, s3_type, *args, **kwargs):
        s3_clz = S3Registry.get_s3_clz(s3_type)
        return s3_clz(*args, **kwargs) if s3_clz else None
