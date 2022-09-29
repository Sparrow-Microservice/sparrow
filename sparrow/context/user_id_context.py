# -*- coding: utf-8 -*-
import base64
from cryptography.fernet import Fernet

from sparrow.context.base_context import ValueContext
from sparrow.context.request_attacher import RequestAttacher
from sparrow.context.utils import expend_headers, get_header_value
from sparrow.extensions.sentry.instance import sentry_switch

USER_ID_KEY = 'USER_ID'
USER_ID_HEADERS = expend_headers('Wish-User-Id')

ENCRYPTED_USER_ID_KEY = 'ENCRYPTED_USER_ID'

# Constants for user id encryption
SEED = 'WISHuser'*4
KEY = base64.urlsafe_b64encode(SEED.encode())
FERNET = Fernet(KEY)


# Suppose that every login of one user will generate a unique session for the following requests,
# until that the user re-login.
class UserIdContext(ValueContext, RequestAttacher):
    stats_key = USER_ID_KEY
    auto_attach = True

    @classmethod
    def set_user_id(cls, user_id, override=False):
        if not user_id:
            return None
        if not override and cls.get():
            # We have already set user id from request headers.
            return None
        user_id = str(user_id)
        cls.set(user_id)
        # set encrypted user id
        try:
            encrypted_user_id = FERNET.encrypt(user_id.encode()).decode()
        except:
            pass
        else:
            EncryptedUserIdContext.set(encrypted_user_id)

        # update user_id in sentry
        if sentry_switch:
            import sentry_sdk
            sentry_sdk.set_user({'id': user_id})


    @classmethod
    def attach_from_request(cls, request, **kwargs):
        user_id = get_header_value(request.headers, USER_ID_HEADERS)
        if user_id:
            try:
                decrypted_user_id = FERNET.decrypt(user_id.encode()).decode()
            except:
                pass
            else:
                cls.set(decrypted_user_id)
                EncryptedUserIdContext.set(user_id)


class EncryptedUserIdContext(ValueContext):
    stats_key = ENCRYPTED_USER_ID_KEY
