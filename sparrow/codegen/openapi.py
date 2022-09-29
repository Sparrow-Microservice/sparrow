import os
from dataclasses import dataclass

from apispec.yaml_utils import dict_to_yaml

from sparrow.base.api import WishApi
from collections import OrderedDict

from sparrow.lib.py_enum import PyEnumMixin
from sparrow.log.meta import LoggingMixin


@dataclass
class MicroClient:
    name: str = None
    generator: str = None
    library: str = None
    micro_request: str = None
    micro_exception: str = None


class ClientType(PyEnumMixin):
    WISHFLASK = MicroClient(
        name='wish-flask', generator='wish-python-client', library='wishFlask'
    )
    WISHPOST = MicroClient(
        name='wishpost', generator='wish-python-client', library='wishTornado'
    )
    WISHWMS = MicroClient(
        name='wishwms', generator='wish-python-client', library='wishTornado',
        micro_request='wishwms.micro.common.request',
        micro_exception='wishwms.micro.common.exceptions'
    )
    WISHRMS = MicroClient(
        name='wishrms', generator='wish-python-client', library='wishTornado',
        micro_request='wishpostrms.micro.common.request',
        micro_exception='wishpostrms.micro.common.exceptions'
    )
    FLASK = MicroClient(
        name='flask', generator='python', library='urllib3'
    )
    TORNADO = MicroClient(
        name='tornado', generator='python', library='tornado'
    )


class OASGen(LoggingMixin):

    spec_order = ['openapi', 'info', 'servers', 'tags', 'paths', 'components', 'security', 'externalDocs']

    @classmethod
    def _get_ordered_specs(cls, specs):
        ordered_specs = OrderedDict()
        for spec in cls.spec_order:
            if spec in specs:
                ordered_specs[spec] = specs.pop(spec)
        for spec in specs:
            ordered_specs[spec] = specs.pop(spec)
        return ordered_specs

    @classmethod
    def _get_specs_yaml(cls, specs):
        specs = cls._get_ordered_specs(specs)
        return dict_to_yaml(specs)

    @classmethod
    def get_full_path(cls, api: WishApi, file_path):
        if not file_path.startswith('/'):
            file_path = os.path.join(api._app.root_path, file_path)
        return file_path

    @classmethod
    def generate_yaml(
            cls,
            api: WishApi,
            file_path=None  # path relative to app.root_path if not absolute path
    ):
        specs = api.spec.to_dict()
        specs_yaml = cls._get_specs_yaml(specs)
        if file_path:
            file_path = cls.get_full_path(api, file_path)
            with open(file_path, 'w') as f:
                f.write(specs_yaml)
            cls.logger.info('Codegen succeeded to %s' % file_path)
        else:
            print(specs_yaml)
            cls.logger.info('Codegen succeeded!')
        return file_path

    @classmethod
    def generate_client_package(
            cls,
            yaml_file,
            client_dir,
            package_name,
            project_name,
            package_version=None,
            git_repo='wish-flask',
            git_owner='ContextLogic',
            client_type=ClientType.WISHFLASK,
            api: WishApi = None,
            **gen_kwargs
    ):
        """

        :param yaml_file: File path of OAS yaml file
        :param client_dir: Location to generate codes
        :param package_name: The client package name. So "import <package_name>" after pip install.
        :param project_name: The client pip project name. So "pip install <project_name>==<package_version>"
        :param package_version: The client pip package version. So "pip install <project_name>==<package_version>".
            None means to use the version of api: <info.version> in the generated schema.
        :param git_repo: The github repo name
        :param git_owner: The owner of this github repo
        :param client_type: The client type to generate.
        :param api: Used to get full path
        :param gen_kwargs: Other args for gen_client
        :return:
        """
        try:
            from openapi_generator_cli import validate, gen_client
        except:
            cls.logger.error('Package wish_openapi_codegen is not installed')
            raise

        if api:
            yaml_file = cls.get_full_path(api, yaml_file)
            client_dir = cls.get_full_path(api, client_dir)

        if isinstance(client_type, str):
            client_type = ClientType.fromstring(client_type)

        # validate the specification file before generating codes
        if validate(yaml_file):

            # Generate python client
            gen_client(yaml_file,
                       client_dir,
                       package_name=package_name,
                       project_name=project_name,
                       package_version=package_version,
                       package_url='https://github.com/%s/%s' % (git_owner, git_repo),
                       git_repo_id=git_repo,
                       git_user_id=git_owner,
                       generator=client_type.generator,
                       library=client_type.library,
                       micro_request=client_type.micro_request,
                       micro_exception=client_type.micro_exception,
                       **gen_kwargs
                       )

