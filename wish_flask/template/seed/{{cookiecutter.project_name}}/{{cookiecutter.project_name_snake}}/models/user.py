try:
    # Try import mongo in case that it is not installed.
    from flask_mongoengine import Document
except:
    Document = None

if Document:
    from mongoengine import ObjectIdField, StringField
    from wish_flask.extensions.mongo.operation import MongoOperation


    class User(Document, MongoOperation):

        user_id = StringField(db_field="uid")
        username = StringField(db_field="u", required=True, min_length=1)
        email = StringField(db_field="e")


# This is a fake user mongo model
class FakeUser(object):

    def __init__(self, user_id=None, username=None, email=None):
        self.user_id = user_id
        self.username = username
        self.email = email

    @classmethod
    def find_one(cls, spec):
        name = spec.get('username') or 'Unknown'
        return cls(user_id='wish001', username=name, email=f'{name}@wish.com')
