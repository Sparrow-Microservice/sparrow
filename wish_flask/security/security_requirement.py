from copy import deepcopy

from wish_flask.security.security import SecurityScheme


class SecurityRequirement(object):
    def __init__(self, *security_schemas: SecurityScheme):
        self.security_schemas = security_schemas
        self._spec = None

    def spec(self):
        if not self._spec:
            self._spec = self.build_spec(*self.security_schemas)
        return deepcopy(self._spec)

    @classmethod
    def build_spec(cls, *security_schemas):
        security_requirement = {}
        for security_schema in security_schemas:
            security_requirement[security_schema.schema_name] = security_schema.scopes
        return security_requirement

    def check(self):
        return all(s.check() for s in self) if self.security_schemas else True

    def __iter__(self):
        for s in self.security_schemas:
            yield s

    @classmethod
    def build_specs(cls, security_requirements):
        specs = []
        security_requirements = security_requirements if isinstance(security_requirements, list) \
            else [security_requirements]
        for s in security_requirements:
            specs.append(s.spec())
        return specs

    @classmethod
    def multi_check(cls, security_requirements):
        if security_requirements and not isinstance(security_requirements, list):
            security_requirements = [security_requirements]
        return any(s.check() for s in security_requirements) if security_requirements else True
