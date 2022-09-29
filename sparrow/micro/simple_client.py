from sparrow.micro.patch_utils import patch_api_kls, patch_client
from sparrow.base.resource import BaseResource
from sparrow.lib.instance_manager import InstanceManager
from sparrow.log.meta import LoggingMixin
from sparrow.utils.convert_utils import to_snake_case


class SimpleClient(BaseResource, LoggingMixin):
    """Simple client for micro clients
    """
    #: (Required) The name of the micro client. It should match with the name in app.config['micro'].
    client_name = None
    #: (Required) The ApiClient class from the generated client package.
    api_client_cls = None

    #: (Required) A list of Api classes from the generated client package, e.g. [PetsApi]
    api_cls_list = None

    #: (Required) The configuration class from the generated client package, or an instance of it.
    client_config = None

    def __init__(self, app=None, micro_config=None):
        """
        :param app: The flask app instance
        :param micro_config: A dict of the app config used to config this client.
            By default, a dict in app.config['micro'][client_name] will be used.
        """

        self.micro_config = micro_config or {}
        self.apis = {}

        super().__init__()
        self.app = app
        # # Set this client to InstanceManger, so we use its proxy anywhere.
        # InstanceManager.get_manager(self.client_name).set_default_obj(self)

        if self.app:
            self.init_app(self.app, self.micro_config)

    @classmethod
    def api_proxy(cls, api):
        """

        :param api: Api class or its string name
        :return: Api proxy
        """
        api_name = api.__name__ if isinstance(api, type) else api
        assert isinstance(api_name, str), 'Wrong type of api'
        api_name = to_snake_case(api_name)
        return InstanceManager.get_manager(cls.client_name).get_obj_proxy(api_name)

    def api(self, api_name):
        return self.apis[api_name]

    def __getattr__(self, item):
        try:
            return self.api(item)
        except:
            return super().__getattribute__(item)

    def init_app(self, app, config=None):
        if config:
            if self.micro_config:
                self.micro_config.update(config)
            else:
                self.micro_config = config
        if app.config.get('micro') and app.config['micro'].get(self.client_name):
            self.micro_config.update(app.config['micro'][self.client_name])
        else:
            self.logger.warn('Config for micro client %s is not found in app', self.client_name)

        self.patch(app.config)
        client_config = self.initiate_config()
        svc_name = app.config.get("service_name")
        client_map = self.initiate_client(client_config, svc_name)
        self.set_apis(client_map)

    def patch(self, app_config):
        # Please patch ApiClient and Api classes
        host = self.micro_config['host']
        patch_client(self.api_client_cls, app_config, host)  # Patch for ApiException
        for api_cls in self.api_cls_list:
            patch_api_kls(api_cls)  # Patch for calling core_run

    def initiate_config(self):
        if not isinstance(self.client_config, type):
            # Got an instance of client configuration, just return it.
            return self.client_config

        host = self.micro_config['host']
        assert host, "Micro client host for %s is not configured" % self.client_name
        auth = self.micro_config['basic_auth']
        assert auth and ':' in auth, "Micro client auth for %s is not properly configured: %s" % (
            self.client_name, auth
        )
        username, pwd = auth.split(':')
        # Initiate config for Api class
        client_config = self.client_config(host=host, username=username, password=pwd)

        # Set additional customized configs

        # (Optionally) Set request timeout for APIs
        # Default is 20
        timeout = self.micro_config.get('timeout')
        if isinstance(timeout, str) and '(' in timeout and ')' in timeout:
            timeout = eval(timeout)
        client_config.request_timeout = timeout
        return client_config

    def initiate_client(self, client_config, svc_name):
        # Initiate client
        # use 'service_name' to init metric client in api_client, if no method service_name means old api client lib
        # old api client lib can't log/metric during request
        if hasattr(self.api_client_cls, 'service_name'):
            api_client = self.api_client_cls(configuration=client_config, service_name=svc_name)
        else:
            api_client = self.api_client_cls(configuration=client_config)
        return {api_cls: api_cls(api_client) for api_cls in self.api_cls_list}

    def set_apis(self, client_map):
        for api_cls in client_map:
            api_name = to_snake_case(api_cls.__name__)
            self.apis[api_name] = client_map[api_cls]
            InstanceManager.get_manager(self.client_name).set_obj(api_name, client_map[api_cls])
