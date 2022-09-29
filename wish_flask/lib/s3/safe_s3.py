import warnings

from wish_flask.lib.s3.exceptions import S3PermissionsError, S3PermissionsWarning
from wish_flask.lib.s3.real_s3 import RealS3


class SafeS3(object):
    """
        Read-only S3 implementation that only supports read operations.
        The use case is for dev machines that want to use prod data, without
        fear of doing bad things to it.

        We explicitly white-list the allowed methods, rather than subclass
        S3Abstraction, out of fear of the base class adding more delete-like
        functions, or us forgetting to black-list everything.
    """

    def __init__(self, *args, **kwargs):
        self.instance = RealS3(*args, **kwargs)

        self.do_allow = (
            "init_app",
            "url",
            "load",
            "load_raw",
            "load_stream",
            "initialize",
            "initialize_bucket",
            "get_bucket_name",
            "exists",
            "last_modified",
            "generate_fetching_url",
            "generate_uploading_url",
            "disconnect",
            "connect",
            "iter_keys"
        )

        self.do_warn = ()

        self.do_error = (
            "destroy",
            "destroy_bucket",
            "save",
            "save_stream",
            "delete",
            "initiate_multipart_upload",
            "upload_part_from_file",
            "complete_multipart_upload"
        )

    def __getattr__(self, attr):
        if attr in self.do_error:
            raise S3PermissionsError("Cannot do S3 '%s' within this environment" % attr)

        if attr in self.do_warn:
            return lambda *args, **kwargs: warnings.warn(
                "Won't do S3 '%s' within this environment" % attr, S3PermissionsWarning
            )

        if attr in self.do_allow:
            return getattr(self.instance, attr)

        raise AttributeError(
            "Unknown attribute %s accessed on ReadOnlyS3Abstraction" % attr
        )
