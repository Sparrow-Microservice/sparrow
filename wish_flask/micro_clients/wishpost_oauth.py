from oauth_client import Configuration, AuthApi, ApiClient
from wish_flask.micro.simple_client import SimpleClient

client_name = 'wishpost_oauth'


class WishpostOauthClient(SimpleClient):
    auto_init = True
    client_name = client_name
    api_client_cls = ApiClient
    api_cls_list = [AuthApi]
    client_config = Configuration


auth_api: AuthApi = WishpostOauthClient.api_proxy(AuthApi)
