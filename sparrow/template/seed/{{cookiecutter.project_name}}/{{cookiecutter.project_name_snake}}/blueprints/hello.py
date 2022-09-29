from collections import defaultdict

from sparrow.base.view import WishMethodView
from sparrow.base.blueprint import WishBlueprint
from sparrow.lib.instance_manager import InstanceManager

from {{cookiecutter.project_name_snake}}.schemas.hello import NameQuerySchema, HelloMsgSchema
from {{cookiecutter.project_name_snake}}.services.user_service import UserService


hello_blp = WishBlueprint(
    'hello', __name__, url_prefix='/api/hello',
    description='Operations on hello'
)

user_service: UserService = InstanceManager.find_obj_proxy(instance_type='user_service')


@hello_blp.route('/')
class Hello(WishMethodView):

    @hello_blp.arguments(NameQuerySchema, location='query')
    @hello_blp.unified_rsp(data_clz=HelloMsgSchema)
    def get(self, name_query: NameQuerySchema):
        name = name_query.name
        user = user_service.find_user(name)
        if user:
            message = f'Hello {user.username} ({user.email})'
        else:
            message = f'No such user {name}'
        return {'message': message}


record = defaultdict(lambda : 0)

# We can decorate a function directly.
@hello_blp.route('/record', methods=['POST'])
@hello_blp.arguments(NameQuerySchema)
@hello_blp.unified_rsp(data_clz=HelloMsgSchema)
def update_pets(query):
    """Record call times"""
    name = query.name
    record[name] += 1
    return {'message': f'{name} called {record[name]} times'}
