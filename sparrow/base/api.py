from apispec.ext.marshmallow import MarshmallowPlugin, resolver
from flask_smorest import Api
from werkzeug.exceptions import HTTPException, UnprocessableEntity

from sparrow.base.blueprint import WishBlueprint
from sparrow.base.schema import RspSchema
from sparrow.security.view_filter import SecurityCheckViewFilter
from sparrow.micro.view_filter import MicroViewFilter
from sparrow.security.security import SecurityScheme
from sparrow.security.security_requirement import SecurityRequirement
from sparrow.exceptions.handlers.http_exp_handler import HttpExceptionHandler, UnprocessableEntityHandler
from sparrow.utils.convert_utils import to_camel_case
from sparrow.utils.iter_utils import iter_recursive


class WishApi(Api):
    ERROR_SCHEMA = RspSchema

    def __init__(self, app=None, *, spec_kwargs=None):
        spec_kwargs = spec_kwargs or {}
        spec_kwargs.setdefault('marshmallow_plugin', MarshmallowPlugin(schema_name_resolver=self.schema_name_resolver))
        self.micro_security_requirements = []
        self.global_security_requirements = []
        self.individual_global_security = False
        super().__init__(app=app, spec_kwargs=spec_kwargs)

    def init_app(self, app, *, spec_kwargs=None):
        self.add_view_filter(app)
        return super().init_app(app, spec_kwargs=spec_kwargs)

    def add_view_filter(self, app):
        from sparrow.application.wish_application import WishFlaskApplication
        if isinstance(app, WishFlaskApplication):
            app.view_filter_chain.add_filter_after(SecurityCheckViewFilter(self), MicroViewFilter.__name__)

    def set_global_security_individually(self):
        self.individual_global_security = True

    @classmethod
    def schema_name_resolver(cls, scheme):
        name = resolver(scheme)
        if getattr(scheme, 'schema_name_ext', None):
            name += to_camel_case(scheme.schema_name_ext, lower_rest=False)
        return name

    def _register_error_handlers(self):
        self._app.register_error_handler(
            HTTPException,
            HttpExceptionHandler(self._app.log_request, app=self._app).handle_exception
        )
        self._app.register_error_handler(
            UnprocessableEntity,
            UnprocessableEntityHandler(self._app.log_request, app=self._app).handle_exception
        )

    def add_security_schema(self, security_schema: SecurityScheme):
        self.spec.components.security_schemes[security_schema.schema_name] = security_schema.spec()

    def add_security_schemas(self, *security_schemas: SecurityScheme):
        for security_schema in security_schemas:
            self.add_security_schema(security_schema)

    def add_micro_security_requirement(self, *security_schemas: SecurityScheme):
        """Add security requirement for all micro blueprints.

        Security requirements will be spread to all micro API operations.
        All security_schemas in this single call will be satisfied for authorization.
        """
        self.add_security_schemas(*security_schemas)
        security_requirement = SecurityRequirement(*security_schemas)
        self.micro_security_requirements.append(security_requirement)

    def add_global_security_requirement(self, *security_schemas: SecurityScheme):
        """Add security requirement for all registered blueprints.

        Security requirements will be spread to all registered API operations.
        All security_schemas in this single call will be satisfied for authorization.
        """
        self.add_security_schemas(*security_schemas)
        security_requirement = SecurityRequirement(*security_schemas)
        if not self.individual_global_security:
            self.spec.options.setdefault('security', []).append(security_requirement.spec())
        self.global_security_requirements.append(security_requirement)

    def add_security_schema_from_requirements(self, security_requirements):
        if security_requirements:
            for s in iter_recursive(security_requirements):
                self.add_security_schema(s)

    def register_blueprint(self, blp, **options):
        if isinstance(blp, WishBlueprint):
            self.add_security_schema_from_requirements(blp.security_requirements)
        super().register_blueprint(blp, **options)
