from io import StringIO
import typing as t

from sparrow.lib.s3.s3_key import BaseS3Key
from sparrow.utils.attr_utils import set_attr_from_config
from sparrow.utils.import_utils import import_string


class BaseS3Abstraction(object):
    def __init__(
            self,
            app=None,
            s3_resource=None,
            bucket_name_enum=None,  # bucket name will be <app_name>-<valid_name>-<bucket-suffix>
            env_prefix=None,  # key prefix
            app_name=None,
            bucket_suffix=None,
            protocol='https',
            host='s3.cn-north-1.amazonaws.com.cn',
            cdn_names=None,
            init_bucket=False,
            physical_bucket=None
    ):
        self.app = app
        self.conn = s3_resource
        self.protocol = protocol
        self.host = host
        self.env_prefix = env_prefix
        self.app_name = app_name
        self.bucket_suffix = bucket_suffix
        self.init_bukcet = init_bucket
        self.physical_bucket = physical_bucket

        self.cdn_names = cdn_names if cdn_names else {}

        self.bucket_name_enum = bucket_name_enum
        self.bucket_names = []

        if self.app:
            self.init_app(self.app)

    def init_app(self, app, config=None):
        self.app = app

        if config:
            set_attr_from_config(self, config, 'protocol')
            set_attr_from_config(self, config, 'host')
            set_attr_from_config(self, config, 'env_prefix')
            set_attr_from_config(self, config, 'app_name')
            set_attr_from_config(self, config, 'bucket_suffix')
            set_attr_from_config(self, config, 'cdn_names')
            set_attr_from_config(self, config, 'bucket_name_enum')
            set_attr_from_config(self, config, 'init_bucket')
            set_attr_from_config(self, config, 'physical_bucket')

        # init app_name
        if self.app_name:
            self.app_name = self.app_name.lower().replace('_', '-')

        # init bucket_suffix
        if self.bucket_suffix:
            self.bucket_suffix = self.bucket_suffix.lower().replace('_', '-')

        # init env_prefix
        self.env_prefix = self.env_prefix or app.env
        if not self.env_prefix:
            raise ValueError('env_prefix is empty in s3')

        if not self.bucket_name_enum:
            raise ValueError('bucket_name_enum is empty in s3')

        self.connect()
        self.initialize()

    def connect(self):
        return

    def disconnect(self):
        self.conn = None

    def initialize(self):
        """initialize all S3 buckets."""
        if isinstance(self.bucket_name_enum, str):
            enum_clz = import_string(self.bucket_name_enum)
            if hasattr(enum_clz, 'get_ids'):
                self.bucket_names = enum_clz.get_ids()
            else:
                raise ValueError('%s is not valid' % self.bucket_name_enum)
        elif isinstance(self.bucket_name_enum, (tuple, list)):
            self.bucket_names = self.bucket_name_enum
        for name in self.bucket_names:
            assert "_" not in name, "Underscore should not be in bucket_names"
        if self.init_bukcet:
            all_buckets = self.all_buckets()
            for name in self.bucket_names:
                full_name = self.get_bucket_name(name)
                if full_name not in all_buckets:
                    self.initialize_bucket(full_name)

    def all_buckets(self):
        return {}

    # pylint: disable=W0613
    def initialize_bucket(self, full_name):
        """initialize given S3 buckets."""
        assert False, "not implemented."

    def iter_keys(self, name, prefix=None) -> t.Iterator[BaseS3Key]:
        assert False, "not implemented."

    def destroy(self):
        """Destroy all S3 buckets."""
        for name in self.bucket_names:
            self.destroy_bucket(self.get_bucket_name(name))

    # pylint: disable=W0613
    def destroy_bucket(self, full_name):
        """Destroy all S3 buckets."""
        assert False, "not implemented."

    def get_bucket_name(self, name):
        """Namespace the given bucket name."""
        if name not in self.bucket_names:
            assert False, "%s is not a valid name." % name
        if self.physical_bucket:
            return self.physical_bucket
        return self._get_bucket_full_name(name)

    def _get_bucket_full_name(self, name):
        names = []
        if self.app_name:
            names.append(self.app_name)
        names.append(name)
        if self.bucket_suffix:
            names.append(self.bucket_suffix)
        return "-".join(names)

    def get_key_name(self, key, name=None):
        """Add prefix to key name

        :param key: key name
        :param name: bucket logical name
        :return:
        """
        key = "%s/%s" % (self.env_prefix, key)
        if self.physical_bucket and name:
            # add logical bucket name if we are putting all objects in a specific physical_bucket.
            key = "%s/%s" % (self._get_bucket_full_name(name), key)
        return key

    # pylint: disable=W0613
    def save(self, name, key, bytes, public=False, content_type=None, cached=False):
        """Save the given str or stream to S3.

        name - name of the bucket, before namespacing.
        key - key inside the given bucket.
        """
        raise NotImplementedError

    def save_stream(self, name, key, stream, public=False):
        """Similar to save(), except accept stream.

        By default, it uses save(), but it can be overriden by subclass
        if more efficient implementation is available.
        """
        bytes = stream.read()
        return self.save(name, key, bytes, public=public)

    def load(self, name, key):  # type: (str, str) -> str
        """Load the given key from S3.

        name - name of the bucket, before namespacing.
        key - key inside the given bucket.
        """
        raise NotImplementedError

    def load_raw(self, name, key):  # type: (str, str) -> bytes
        """Load the given key from S3.

        name - name of the bucket, before namespacing.
        key - key inside the given bucket.
        """
        raise NotImplementedError

    def load_stream(self, name, key):
        """Similar to load(), except returns a stream.


        By default, it uses load(), but it can be overriden by subclass
        if more efficient implementation is available.
        """
        result = self.load(name, key)
        return StringIO(result)

    def delete(self, name, key):
        raise NotImplementedError

    # pylint: disable=W0613
    def url(self, name, key, try_cdn=True):
        """
        Return the URL to the given object.
        """
        raise NotImplementedError

    def generate_uploading_url(self, name, key, **kwargs):
        """
        Return the presigned uploading URL to the given object.
        """
        raise NotImplementedError

    def generate_fetching_url(self, name, key, **kwargs):
        """
        Return the presigned fetching URL to the given object.
        """
        raise NotImplementedError

    def exists(self, name, key):
        """
        returns true if the object of key exists in bucket name
        """
        raise NotImplementedError

    def last_modified(self, name, key):
        """
        return the epoch second of the object's modified time
        """
        raise NotImplementedError

    def get_size(self, name, key):
        """
        return the size of the object of key
        """
        raise NotImplementedError

    def initiate_multipart_upload(self, name, key, content_type=None, cached=False):
        raise NotImplementedError

    def upload_part_from_file(self, name, key, upload_id, bytes, part_num):
        raise NotImplementedError

    def complete_multipart_upload(self, name, key, upload_id, public=True):
        raise NotImplementedError
