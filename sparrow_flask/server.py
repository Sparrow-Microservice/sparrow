from sparrow_flask.creation import create_app
import os

app = create_app(os.getenv('FLASK_ENV'))

from sparrow_flask.blueprints.hello import hello_blp
from sparrow_flask.blueprints.hello2 import hello2

app.register_route(hello_blp)
app.put('/api/hello2')(hello2)

if __name__ == '__main__':
    app.run()
