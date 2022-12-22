from sparrow_flask.creation import create_app
from sparrow_flask.blueprints.hello import hello_blp
import os

app = create_app(os.getenv('FLASK_ENV'))
app.register_api(hello_blp)

if __name__ == '__main__':
    app.run()