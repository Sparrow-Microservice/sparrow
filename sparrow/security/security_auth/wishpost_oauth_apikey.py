from sparrow.security.security import APIKey
from sparrow.micro_clients.wishpost_oauth import auth_api
from flask import request
from oauth_client.models.get_session_pack_request import GetSessionPackRequest
from oauth_client.models.get_session_pack_response import GetSessionPackResponse
from sparrow.schema.user import UserSchema
from sparrow.context.user_id_context import UserIdContext
from flask import current_app
from sparrow.utils.import_utils import import_string


def check_have_cache_manager():
    extension = current_app.config.get('extensions', None)
    if not extension:
        return False
    cache_manager = extension.get('cache_manager', None)
    if not cache_manager:
        return False
    enabled = cache_manager.get('enabled', False)
    return enabled

def _get_session_pack_response(session_key):
    session_pack: GetSessionPackResponse = auth_api.get_session_pack_post(
        get_session_pack_request=GetSessionPackRequest(
            session_key=session_key))
    return session_pack


class WishpostOauthAPIKey(APIKey):
    def __init__(self, required_permissions, required_roles):
        self.required_permissions = required_permissions
        self.required_roles = required_roles
        super(WishpostOauthAPIKey, self).__init__('WishpostOauth', 'session',
                                                  'header')

    def _cache_get_session_pack_response(self):
        if hasattr(self, '_f'):
            return getattr(self, '_f')
        have_cache_manager = check_have_cache_manager()
        if not have_cache_manager:
            return _get_session_pack_response

        wishpost_oauth = current_app.config.get('wishpost_oauth', None)
        if wishpost_oauth is None:
            return _get_session_pack_response

        cache_manager = wishpost_oauth.get('cache_manager', None)
        if cache_manager is None:
            return _get_session_pack_response

        cache_manager_wishpost_oauth = import_string(
            'sparrow.extensions.cache_manager.instance.cache_manager_' + cache_manager)

        self._f = cache_manager_wishpost_oauth.cache(local_cache_switch=True)(
            _get_session_pack_response)
        return self._f

    def check(self):
        # 1. get session key from cookie
        session_key = request.cookies.get("session") or request.headers.get("session")
        if not session_key:
            return False

        session_pack = self._cache_get_session_pack_response()(session_key)
        if not session_pack or not session_pack.is_valid:
            return False

        user_permissions = session_pack.permissions
        user_role = session_pack.roles

        # check permissions
        if not any(
                ele in self.required_permissions for ele in user_permissions):
            return False

        # check role
        if not any(ele in self.required_roles for ele in user_role):
            return False

        user = UserSchema(user_id=session_pack.user_id,
                          user_permissions=user_permissions,
                          user_roles=user_role)

        request.user = user
        UserIdContext.set_user_id(user.user_id)

        return True
