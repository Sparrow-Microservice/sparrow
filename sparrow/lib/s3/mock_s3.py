import os
import uuid
from shutil import rmtree

from flask import send_from_directory

from sparrow.lib.s3.abstract_s3 import BaseS3Abstraction
from sparrow.lib.s3.s3_key import BaseS3Key
from sparrow.utils.attr_utils import set_attr_from_config


class MockS3Key(BaseS3Key):
    def __init__(self, fpath, bucket_name, **kwargs):
        super().__init__(**kwargs)
        self._bucket_name = bucket_name
        self._fpath = fpath

    @property
    def bucket_name(self) -> str:
        return self._bucket_name

    @property
    def key(self) -> str:
        return self._fpath

    @property
    def logical_key(self) -> str:
        if self._key_prefix:
            return self.key.replace(self._key_prefix, '')
        return self.key

    @property
    def data(self) -> str:
        return self.raw_data.decode('utf-8')

    @property
    def raw_data(self) -> bytes:
        with open(self._fpath, "rb") as f:
            return f.read()


class MockS3(BaseS3Abstraction):
    """Mock implementation of S3Abstraction. Uses filesystem."""

    def __init__(self,
                 *args,
                 root_path=None,  # file root directory
                 uri_prefix=None,  # uri prefix to get file
                 init_bucket=True,
                 **kwargs):
        self.root_path = root_path
        self.uri_prefix = uri_prefix
        super().__init__(*args, init_bucket=init_bucket, **kwargs)

    def init_app(self, app, config=None):
        if config:
            set_attr_from_config(self, config, 'root_path')
            set_attr_from_config(self, config, 'uri_prefix')

        self.root_path = self.root_path or (app.static_folder + '_s3')
        self.uri_prefix = self.uri_prefix or (app.static_url_path + '-s3')
        if not self.uri_prefix.startswith('/'):
            raise ValueError('uri_prefix should start with /')

        if not os.path.isabs(self.root_path):
            self.root_path = os.path.join(app.root_path, self.root_path)
        super().init_app(app, config=config)
        self.register_endpoint(app)

    def register_endpoint(self, app):
        app.add_url_rule(
            self.uri_prefix + "/<path:filename>",
            endpoint="s3_mock",
            view_func=self.send_s3_file,
        )

    def send_s3_file(self, filename):
        return send_from_directory(self.root_path, filename, cache_timeout=0)

    def _get_dirname(self, full_name):
        # get abs bucket path
        return os.path.join(self.root_path, full_name)

    def _get_filename(self, name, key):
        full_name = self.get_bucket_name(name)
        key = self.get_key_name(key, name=name)
        dirname = self._get_dirname(full_name)
        return os.path.join(dirname, key)

    def _get_filename_with_ensure_dir(self, name, key):
        filename = self._get_filename(name, key)
        dir_name = os.path.dirname(filename)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        return filename

    def initialize_bucket(self, full_name):
        dirpath = self._get_dirname(full_name)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        assert os.path.isdir(dirpath), (
            "%s is not directory, but it's going to be used to store files."
        ) % dirpath

    def destroy_bucket(self, full_name):
        dirpath = self._get_dirname(full_name)
        if os.path.exists(dirpath):
            rmtree(dirpath)

    def iter_keys(self, name, prefix=None):
        ftarget = self._get_filename(name, prefix or '')
        dirname = os.path.dirname(ftarget)
        full_name = self.get_bucket_name(name)
        raw_key_prefix = self._get_filename(name, '')
        for dirpath, dnames, fnames in os.walk(dirname):
            for fname in fnames:
                fpath = os.path.join(dirpath, fname)
                if fpath.startswith(ftarget):
                    yield MockS3Key(fpath,
                                    full_name,
                                    logical_bucket_name=name,
                                    key_prefix=raw_key_prefix)

    # pylint: disable=W0613
    def initiate_multipart_upload(self, name, key, content_type=None, cached=False):
        """
            create a master id file to keep track of the filename and all the
            parts that comes in
        """
        upload_id = uuid.uuid1().hex
        upload_key = "%s.0" % upload_id
        try:
            id_file = self._get_filename_with_ensure_dir(name, upload_key)
            with open(id_file, "w") as f:
                f.write("%s\n" % key)
        except Exception:
            self.delete(name, upload_key)

        return upload_id

    def upload_part_from_file(self, name, key, upload_id, bytes, part_num):
        # write part
        upload_key = "%s.%s" % (upload_id, part_num)
        id_file = self._get_filename_with_ensure_dir(name, upload_key)
        try:

            with open(id_file, "wb") as f:
                f.write(self.to_bytes(bytes))
        except Exception:
            self.delete(id_file, upload_key)

        # update master with new part
        upload_key = "%s.0" % upload_id
        try:
            id_file = self._get_filename_with_ensure_dir(name, upload_key)
            with open(id_file, "a") as f:
                f.write("%s\n" % part_num)
        except Exception:
            self.delete(id_file, upload_key)

    def complete_multipart_upload(self, name, key, upload_id, public=True):
        # get the original file name and list of parts
        id_name = "%s.0" % upload_id
        id_file = self._get_filename(name, id_name)
        with open(id_file, 'r') as f:
            file_info = [line.rstrip() for line in f.readlines()]
        self.delete(name, id_name)

        # make sure we have all the parts
        parts = [int(part) for part in file_info[1:]]
        parts.sort()
        check_parts = set(range(1, parts[-1] + 1)) - set(parts)
        if len(check_parts) != 0:
            raise Exception("missing parts")

        # combine the parts
        try:
            filename = self._get_filename_with_ensure_dir(name, file_info[0])
            with open(filename, "wb") as f:
                for part in parts:
                    upload_key = "%s.%s" % (upload_id, part)
                    part_name = self._get_filename(name, upload_key)
                    with open(part_name, "rb") as part_file:
                        f.write(part_file.read())
                    self.delete(name, upload_key)
        except Exception:
            self.delete(name, file_info[0])

    @classmethod
    def to_bytes(cls, content):
        return content.encode() if isinstance(content, str) else content

    def save(self, name, key, bytes, public=False, content_type=None, cached=False):
        filename = self._get_filename_with_ensure_dir(name, key)
        try:
            with open(filename, 'wb') as f:
                f.write(self.to_bytes(bytes))
        except Exception:
            self.delete(name, key)

    def load(self, name, key):
        data = self.load_raw(name, key)
        if isinstance(data, bytes):
            return data.decode()

    def load_raw(self, name, key):
        filename = self._get_filename(name, key)
        with open(filename, "rb") as f:
            return f.read()

    def delete(self, name, key):
        filename = self._get_filename(name, key)
        if not os.path.exists(filename):
            return
        os.remove(filename)

    def url(self, name, key, try_cdn=True):
        path = os.path.join(self.get_bucket_name(name), self.get_key_name(key, name=name))
        rt = [self.protocol, "://", self.host, self.uri_prefix, '/', path]
        return ''.join(rt)

    def generate_fetching_url(self, name, key, **kwargs):
        # Under mock-s3, we use original url() method for simplicity
        return self.url(name, key)

    def generate_uploading_url(self, name, key, **kwargs):
        return self.url(name, key)

    def exists(self, name, key):
        filename = self._get_filename(name, key)
        return os.path.exists(filename)

    def last_modified(self, name, key):
        filename = self._get_filename(name, key)
        return os.path.getmtime(filename)

    def get_size(self, name, key):
        filename = self._get_filename(name, key)
        return os.path.getsize(filename)
