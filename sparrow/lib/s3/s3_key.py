class BaseS3Key(object):
    def __init__(self, logical_bucket_name=None, key_prefix=None):
        self._logical_bucket_name = logical_bucket_name
        self._key_prefix = key_prefix

    @property
    def bucket_name(self) -> str:
        """The bucket name of this key.
        e.g. wishpostrms-data
        """
        raise NotImplementedError

    @property
    def logical_bucket_name(self):
        """The logical bucket name of this key.
        Can be used in BaseS3Abstraction functions directly.
        e.g. data
        """
        return self._logical_bucket_name

    @property
    def key(self) -> str:
        """The key name (path) of this key
        e.g. dev/tmp/log.txt
        """
        raise NotImplementedError

    @property
    def logical_key(self) -> str:
        """The logical key name (path) of this key.
        Can be used in BaseS3Abstraction functions directly.
        e.g. tmp/log.txt
        """
        raise NotImplementedError

    @property
    def data(self) -> str:
        """The data value of this key
        """
        raise NotImplementedError

    @property
    def raw_data(self) -> bytes:
        """The raw data value of this key
        """
        raise NotImplementedError
