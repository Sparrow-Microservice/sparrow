from sparrow_flask.creation import create_app, create_api
from sparrow_flask.blueprints.hello import hello_blp

app = create_app(__name__)

api = create_api(app)
api.register_blueprint(hello_blp)

if __name__ == '__main__':
    app.run()