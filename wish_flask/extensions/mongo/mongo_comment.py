import threading
import socket
import traceback


class MongoComment(object):
    _ip = None
    AUTO_FRAME_LIMIT = 10
    AUTO_BLACKLIST = (
        'mongoengine/base.py',
        'mongoengine/document.py',
    )

    # If we override any base methods upstream in a child document class,
    # we need to go up one more stack to get the proper comment
    FUNCTION_BLACKLIST = ('find_raw', 'find', 'update', 'insert')

    @classmethod
    def blacklisted(cls, filename):
        return any(filename.endswith(bl) for bl in cls.AUTO_BLACKLIST)

    @classmethod
    def function_blacklisted(cls, function_name):
        return function_name in cls.FUNCTION_BLACKLIST

    @classmethod
    def context(cls, filename):
        if not filename.startswith('/'):
            return filename
        return '/'.join(filename.split('/')[4:])

    @classmethod
    def get_query_comment(cls):
        """
        Retrieves comment from greenlet if called in one, else examine stack
        """
        return cls.get_comment()

    @classmethod
    def get_comment(cls):
        try:
            if cls._ip == None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect(('8.8.8.8', 80))
                cls._ip = sock.getsockname()[0]
                sock.close()

            last_stacks = traceback.extract_stack(limit=cls.AUTO_FRAME_LIMIT)
            for i in range(-3, -len(last_stacks) - 1, -1):
                filename, line, functionname, text = last_stacks[i]

                if cls.blacklisted(filename):
                    continue

                if cls.function_blacklisted(functionname):
                    continue

                msg = '[%s]%s @ %s:%s' % (
                    cls._ip, functionname, cls.context(filename), line
                )
                return msg
            return 'ERROR: Could not retrieve external stack frame'
        except:
            return 'ERROR: Failed to get comment'
