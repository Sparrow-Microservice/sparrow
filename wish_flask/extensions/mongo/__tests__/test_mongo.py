# -*- coding: utf-8 -*-

import pymongo
import warnings
import contextlib
from mongoengine import connect
from flask_mongoengine import Document
from wish_flask.extensions.mongo.operation import MongoOperation, \
    _transform_value, _transform_key, _transform_id_reference_value, \
    FieldNotLoadedError, _transform_hint, BulkOperationError
import mongoengine.base
import unittest
from mongoengine import StringField, IntField, EmbeddedDocumentField, ListField, \
    DictField, ObjectIdField, ReferenceField, EmbeddedDocument, BooleanField
from mongoengine.connection import _get_db
from bson import ObjectId, DBRef


class CustomQueryTest(unittest.TestCase):
    def setUp(self) -> None:
        connect()
        # self.db = _get_db()
        mongoengine.base._document_registry = {}

        class Colour(EmbeddedDocument):
            meta = {'allow_inheritance': False}
            name = StringField(db_field='n')

            def __str__(self):
                return self.name

            def __eq__(self, other):
                return isinstance(other, Colour) and self.name == other.name

        class User(Document, MongoOperation):
            meta = {'allow_inheritance': False}
            id = ObjectIdField(primary_key=True)
            name = StringField()

        class Person(Document, MongoOperation):
            meta = {'allow_inheritance': False}  # allow_inheritance 是否可以被继承
            INCLUDE_SHARD_KEY = ['shard_key']  # ?
            name = StringField()
            age = IntField(db_field='a')
            gender = StringField(db_field='g')
            favourite_colour = EmbeddedDocumentField(Colour, db_field='c')
            other_colours = ListField(
                EmbeddedDocumentField(Colour), db_field='o')
            number_list = ListField(IntField())
            arbitrary_dict = DictField()
            dbfield_dict = DictField(db_field='d')
            some_id = ObjectIdField()
            id_list = ListField(ObjectIdField())
            user = ReferenceField(User, dbref=True)  # todo: 一定要加 dbref
            friends = ListField(ReferenceField("self", dbref=True))
            shard_key = StringField(db_field='s')

        class Vehicle(Document, MongoOperation):
            meta = {'allow_inheritance': True}
            name = StringField()

        class Bike(Vehicle):
            has_bell = BooleanField()

        class Scooter(Vehicle):
            cc = IntField()

        class Shard(Document, MongoOperation):
            hash = IntField(db_field='h')
            name = StringField()

            def _update_one_key(self):
                return {'_id': self.id, 'hash': 12}

        Person._pymongo().drop()  # ?
        User._pymongo().drop()  # ?
        Vehicle._pymongo().drop()
        Bike._pymongo().drop()
        Scooter._pymongo().drop()
        Shard._pymongo().drop()

        self.Person = Person
        self.Colour = Colour
        self.User = User
        self.Vehicle = Vehicle
        self.Bike = Bike
        self.Scooter = Scooter
        self.Shard = Shard

    def tearDown(self):
        self.Person.objects.delete()

    def testInOnEnbeddedDocumentList(self):
        blue = self.Colour(name="Blue")
        red = self.Colour(name="Red")
        yellow = self.Colour(name="Yellow")
        p = self.Person(name="Adam", favourite_colour=blue)
        p.save()
        p = self.Person(name="Bill", favourite_colour=red)
        p.save()
        p = self.Person(name="Billy", favourite_colour=yellow)
        p.save()
        people = self.Person.find({'favourite_colour': {'$in': [
            blue,
            red,
            yellow,
        ]}})

        self.assertEqual(len(people), 3)

    def testTransformQuery(self):
        query = {'$set': {'name': 'Chu', 'age': 20}}
        result = _transform_value(query, self.Person)

        self.assertEqual(result, {'$set': {'name': 'Chu', 'a': 20}})

    def testTransformQueryEmbedded(self):
        blue = self.Colour(name='Blue')
        query = {'$set': {'name': 'Chu', 'age': 20, 'favourite_colour': blue}}
        result = _transform_value(query, self.Person)

        self.assertEqual(set(result['$set'].keys()), set(['name', 'a', 'c']))

        self.assertEqual(result['$set']['name'], 'Chu')
        self.assertEqual(result['$set']['c'], {'n': 'Blue'})

    def testTransformQueryList(self):
        blue = self.Colour(name='Blue')
        red = self.Colour(name='Red')
        query = {
            '$set': {'name': 'Chu', 'age': 20, 'other_colours': [red, blue]}}
        result = _transform_value(query, self.Person)

        self.assertEqual(set(result['$set'].keys()), set(['name', 'a', 'o']))

        self.assertEqual(result['$set']['name'], 'Chu')
        self.assertEqual(result['$set']['o'], [{'n': 'Red'}, {'n': 'Blue'}])

        query = {'name': 'Chu', 'age': 20, 'other_colours': red}
        result = _transform_value(query, self.Person)

        self.assertEqual(set(result.keys()), set(['name', 'a', 'o']))

        self.assertEqual(result['name'], 'Chu')
        self.assertEqual(result['o'], {'n': 'Red'})

    def testTransformQueryOr(self):
        blue = self.Colour(name='Blue')
        red = self.Colour(name='Red')
        query = {'$or': [{'name': 'Chu'}, {'age': 20}]}
        result = _transform_value(query, self.Person)
        self.assertEqual(set(result.keys()), set(['$or']))
        self.assertEqual(set(list(x.keys())[0] for x in result['$or']),
                         set(['name', 'a']))
        self.assertEqual(result['$or'][0]['name'], 'Chu')
        self.assertEqual(result['$or'][1]['a'], 20)

        query = {'$and': [{'name': 'Chu'}, {'$or': [{'age': 20}, {'age': 21}]}]}
        result = _transform_value(query, self.Person)

        self.assertEqual(set(result.keys()), set(['$and']))
        self.assertEqual(set([list(x.keys())[0] for x in result['$and']]),
                         set(['name', '$or']))
        self.assertEqual(result['$and'][0]['name'], 'Chu')
        self.assertEqual([list(x.keys())[0] for x in result['$and'][1]['$or']],
                         ['a', 'a'])
        self.assertEqual(result['$and'][1]['$or'][0]['a'], 20)
        self.assertEqual(result['$and'][1]['$or'][1]['a'], 21)

    def testTransformQueryListIndex(self):
        blue = self.Colour(name='Blue')
        query = {'$set': {'other_colours.1': blue}}
        result = _transform_value(query, self.Person)

        self.assertEqual(result, {'$set': {'o.1': {'n': 'Blue'}}})

        query = {'$set': {'other_colours.1.name': 'Red'}}
        result = _transform_value(query, self.Person)

        self.assertEqual(result, {'$set': {'o.1.n': 'Red'}})

    def testTransformQueryDictOp(self):
        query = {'dbfield_dict': {'$gt': {}}}

        result = _transform_value(query, self.Person)

        self.assertEqual(result, {'d': {'$gt': {}}})

    def testDictEncoding(self):
        p = self.Person(name="Adam", age=21)
        p.save()
        val = {'x': 4, 'c': self.Colour(name="Blue")}
        p.arbitrary_dict = val
        p.save()

        p.reload()
        self.assertEqual(p.arbitrary_dict, val)

        query = {'$set': {'arbitrary_dict.x': 42,
                          'age': 12,
                          'arbitrary_dict.c.n': 'Red'}}
        transformed = _transform_value(query, self.Person)

        self.assertEqual(transformed['$set']['arbitrary_dict.x'], 42)
        self.assertEqual(transformed['$set']['arbitrary_dict.c.n'], 'Red')
        self.assertEqual(transformed['$set']['a'], 12)
        self.assertEqual(len(transformed), 1)
        self.assertEqual(len(transformed['$set']), 3)

        # p.update_one(query)
        # self.assertEqual(p.age, 12)
        # self.assertEqual(p.arbitrary_dict['x'], 4)
        # self.assertEqual(p.arbitrary_dict['c']['n'], "Blue")
        #
        # p.reload()
        # self.assertEqual(p.age, 12)
        # self.assertEqual(p.arbitrary_dict['x'], 42)
        # self.assertEqual(p.arbitrary_dict['c']['n'], "Red")

    def testObjectIdEncoding(self):
        p = self.Person(some_id='0' * 24)
        p.save()

        self.assertEqual(p.find({'some_id': '0' * 24}), [p])

        p.reload()

        self.assertEqual(p.some_id, ObjectId('0' * 24))

    def testDocumentIds(self):
        user = self.User(id=ObjectId())
        user.save()
        uid = user.id

        self.assertEqual(user.find({'_id': uid}), [user])
        self.assertEqual(user.find_one({'_id': uid}), user)

        p = self.Person()
        p.save()

        self.assertEqual(p.find({'_id': p.id}), [p])

    def testSort(self):
        p1 = self.Person(age=10)
        p1.save()
        p2 = self.Person(age=15)
        p2.save()
        p3 = self.Person(age=20)
        p3.save()

        self.assertEqual(self.Person.find({}, sort=[('age', 1)]), [p1, p2, p3])
        self.assertEqual(self.Person.find({}, sort=[('age', -1)]),
                         [p3, p2, p1])
        self.assertRaises(ValueError, self.Person.find, {}, sort=['age'])
        self.assertRaises(ValueError, self.Person.find, {}, sort='age')

    def testIncludeFields(self):
        p = self.Person(age=10, name="Adam")
        p.save()

        p1 = self.Person.find_one({'age': 10})
        self.assertEqual(p1, p)

        p1 = self.Person.find_one({'age': 10}, fields=['age'])
        self.assertEqual(p1.age, 10)
        self.assertEqual(p1.name, None)

        p1 = self.Person.find_one({'age': 10}, fields=['age', 'name'])
        self.assertEqual(p1, p)

        p1 = self.Person.find_one({'age': 10}, fields={'age': 0})  # 除了 age 都要
        # with self.assertRaises(FieldNotLoadedError):
        #     getattr(p1, 'age') # 现在只会返回 None
        self.assertEqual(p1.name, 'Adam')
        self.assertEqual(p1.age, None)

        p1 = self.Person.find_one({'age': 10}, fields={'name': 0})
        self.assertEqual(p1.age, 10)
        self.assertEqual(p1.name, None)

        p1 = self.Person.find_one({'age': 10}, fields={'age': 1})
        self.assertEqual(p1.age, 10)
        self.assertEqual(p1.name, None)

    def testExcludeFields(self):
        p = self.Person(age=10, name='Patrick')
        p.save()

        p1 = self.Person.find_one({'name': 'Patrick'}, excluded_fields=['name'])
        self.assertEqual(p1.id, p.id)
        self.assertEqual(p1.age, 10)
        self.assertEqual(p1.name, None)

        p2 = self.Person.find_one(
            {'name': 'Patrick'},
            excluded_fields=['name', 'age']
        )

        self.assertEqual(p2.id, p.id)
        self.assertEqual(p2.age, None)
        self.assertEqual(p2.name, None)

    def testIncludeAndExcludeFields(self):
        p = self.Person(age=10, name='Sorey')
        p.save()

        with self.assertRaises(ValueError):
            self.Person.find_one(
                {'name': 'Sorey'},
                fields=['age'],
                excluded_fields=['name']
            )

    def testSlice(self):
        p = self.Person(age=10, name='Sean', number_list=[1, 5, 3, 19, 15, -1])
        p.save()

        p1 = self.Person.find_one(
            {'name': 'Sean'},
            fields={'number_list': {'$slice': [3, 2]}}
        )

        self.assertEqual(p1.id, p.id)
        self.assertEqual(p1.number_list, [19, 15])
        self.assertEqual(p1.name, p.name)

        p2 = self.Person.find_one(
            {'name': 'Sean'},
            fields={'number_list': {'$slice': -2}, 'name': 0}
        )

        self.assertEqual(p2.id, p.id)
        self.assertEqual(p2.number_list, [15, -1])
        self.assertEqual(p2.name, None)

        p3 = self.Person.find_one(
            {'name': 'Sean'},
            fields={'number_list': {'$slice': (3, 2)}}
        )
        self.assertEqual(p3.id, p1.id)
        self.assertEqual(p3.number_list, p1.number_list)

    def testElemmatch(self):
        p = self.Person(age=10, name='Sean', number_list=[1, 5, 3, 19, 15, -1])
        p.save()

        p1 = self.Person.find_one(
            {'name': 'Sean'},
            fields={'number_list': {'$elemMatch': {'$gte': 10, '$lt': 18}}}
        )

        self.assertEqual(p1.id, p.id)
        self.assertEqual(p1.number_list, [15])
        self.assertEqual(p1.name, None)

        p2 = self.Person.find_one(
            {'name': 'Sean'},
            fields={'number_list': {'$elemMatch': {'$gte': 2, '$lt': 6}},
                    'name': 1}
        )
        self.assertEqual(p2.id, p.id)
        self.assertEqual(p2.number_list, [5])
        self.assertEqual(p2.name, p.name)

        blue1 = self.Colour(name='blue')
        blue2 = self.Colour(name='blue')
        red = self.Colour(name='red')
        q = self.Person(age=13, name='Sean', other_colours=[blue1, red, blue2])
        q.save()

        q1 = self.Person.find_one(
            {'other_colours': {'$elemMatch': {'name': 'blue'}}})
        self.assertEqual(q1.id, q.id)

        q2 = self.Person.find_one(
            {'age': 13},
            fields={'other_colours': {'$elemMatch': {'name': 'blue'}}})

        self.assertEqual(q2.id, q.id)
        self.assertEqual(q2.other_colours, [blue1])

    def testQueryIn(self):
        query = {'_id': {'$in': [ObjectId(), ObjectId(), ObjectId()]}}
        self.assertEqual(_transform_value(query, self.User), query)

    def testAutoObjId(self):
        obj_ids = [ObjectId(), ObjectId(), ObjectId()]
        in_query = {'_id': {'$in': [str(o) for o in obj_ids]}}
        out_query = _transform_value(in_query, self.User)

        self.assertEqual(out_query['_id']['$in'], obj_ids)

        u1 = self.User(id=ObjectId())
        u1.save()
        u2 = self.User(id=ObjectId())
        u2.save()

        users = self.User.find({'_id': {'$in': [str(u1.id), str(u2.id)]}})

        self.assertEqual(users, [u1, u2])

    def testOnlyId(self):
        p = self.Person(name="Adam")
        p.save()

        p1 = self.Person.find_one({'name': 'Adam'}, fields=['id'])
        self.assertEqual(p1.id, p.id)
        self.assertEqual(p1.name, None)

        p2 = self.Person.find_one({'name': 'Adam'}, fields=['_id'])  # 会 raise
        self.assertEqual(p2.id, p.id)
        self.assertEqual(p2.name, None)

    def testInheritanceBaseClass(self):
        v = self.Vehicle(name='Honda')
        b = self.Bike(name='Fixie')
        s = self.Scooter(name='Zoom', cc=110)
        v.save()
        b.save()
        s.save()

        qs = self.Vehicle.objects.exclude('id').as_pymongo()
        qs2 = self.Bike.objects.exclude('id').as_pymongo()
        qs3 = self.Scooter.objects.exclude('id').as_pymongo()

        self.assertEqual(self.Vehicle.count({}), 3)
        self.assertEqual(self.Vehicle.count({'name': 'Fixie'}), 1)
        self.assertEqual(self.Vehicle.count({'name': 'Honda'}), 1)
        ret = self.Scooter.update_doc({'name': 'Zoom'}, {'$set': {'cc': 400}})
        self.assertEqual(ret, 1)
        s2 = self.Vehicle.find_one({'name': 'Zoom'})
        self.assertEqual(s2.cc, 400)

    def testInheritanceSubClass(self):
        v = self.Vehicle(name="Honda")
        b = self.Bike(name="Fixie")
        b2 = self.Bike(name="Honda")
        s = self.Scooter(name="Zoom", cc=110)
        v.save()
        b.save()
        b2.save()
        s.save()

        self.assertEqual(self.Vehicle.count({}), 4)
        self.assertEqual(self.Bike.count({}), 2)
        self.assertEqual(self.Scooter.count({}), 1)
        self.assertEqual(self.Vehicle.count({'name': 'Fixie'}), 1)
        self.assertEqual(self.Bike.count({'name': 'Fixie'}), 1)
        self.assertEqual(self.Vehicle.count({'name': 'Honda'}), 2)
        self.assertEqual(self.Bike.count({'name': 'Honda'}), 1)

        ret = self.Bike.update_doc({'name': 'Honda'},
                                   {'$set': {'name': 'Sarengetti'}})
        self.assertEqual(ret, 1)
        self.assertEqual(self.Vehicle.count({'name': 'Honda'}), 1)
        self.assertEqual(self.Vehicle.count({'name': 'Sarengetti'}), 1)
        self.assertEqual(self.Bike.count({'name': 'Honda'}), 0)
        self.assertEqual(self.Bike.count({'name': 'Sarengetti'}), 1)

    def testUpdateOne(self):
        s1 = self.Shard(hash=14, name='s1')
        s2 = self.Shard(hash=12, name='s2')
        s1.save()
        s2.save()
        ret = s1.update_one({'$set': {'name': 'changed'}})
        self.assertEqual(ret, 1)
        self.assertEqual(s1.name, 'changed')

    def testFindIter(self):
        people = [self.Person(age=a) for a in [10, 15, 20]]
        for p in people:
            p.save()

        for i, p in enumerate(self.Person.find_iter({}, sort=[('age', 1)])):
            self.assertEqual(p, people[i])

        for i, p in enumerate(self.Person.find_iter({'age': {'$lte': 15}},
                                                    sort=[('age', 1)])):
            self.assertEqual(p, people[i])

    def testMultiUpdate(self):
        people = [self.Person(age=a) for a in [10, 15, 20]]
        for p in people:
            p.save()

        self.assertEqual(self.Person.count({'age': {'$lte': 15}}), 2)

        ret = self.Person.update_doc({'age': {'$lte': 15}},
                                     {'$set': {'name': 'Adam'}}, multi=False)
        self.assertEqual(ret, 1)

        ret = self.Person.update_doc({'age': {'$lte': 15}},
                                     {'$set': {'name': 'Adam'}})
        self.assertEqual(ret, 2)

        for p in people:
            p.reload()
            self.assertEqual(p.name, 'Adam' if p.age <= 15 else None)

    def testCount(self):
        people = [self.Person(age=a) for a in [10, 15, 20]]
        for p in people:
            p.save()

        self.assertEqual(self.Person.count({'age': {'$lte': 15}}), 2)
        self.assertEqual(self.Person.count({'name': 'Adam'}), 0)
        self.assertEqual(self.Person.count({'age': {'$lte': 35}}), 3)
        self.assertEqual(self.Person.count({'age': {'$lte': 0}}), 0)
        self.assertEqual(self.Person.count({'age': 10}), 1)

    def testReferences(self):
        user = self.User(id=ObjectId(), name='Adam A Flynn')
        user.save()
        person = self.Person(user=user, name='Adam')
        person.save()

        spec = _transform_value({'user': user}, self.Person)
        self.assertEqual(spec, {'user': DBRef('user', user.id)})
        p = self.Person.find_one({'user': user})
        self.assertEqual(p.user.id, user.id)
        self.assertEqual(p.user.name, 'Adam A Flynn')
        self.assertEqual(p.name, 'Adam')

    def testReferenceList(self):
        adam = self.Person(name='Adam')
        adam.save()
        josh = self.Person(name='Josh')
        josh.save()
        chu = self.Person(name='Chu')
        chu.save()
        danny = self.Person(name='Danny', friends=[adam, josh])
        danny.save()

        q = _transform_value({'friends': chu}, self.Person)
        self.assertEqual(q['friends'], DBRef("person", chu.id))

        q = _transform_value({'friends': DBRef("person", chu.id)}, self.Person)
        self.assertEqual(q['friends'], DBRef('person', chu.id))

        q = _transform_value(
            {'friends': {'$in': (DBRef('person', chu.id), adam)}}, self.Person)
        self.assertEqual(len(q['friends']['$in']), 2)
        self.assertTrue(DBRef("person", chu.id) in q['friends']['$in'])
        self.assertTrue(DBRef('person', adam.id) in q['friends']['$in'])

        q2 = _transform_value(
            {'friends': {'$in': [DBRef('person', chu.id), adam]}}, self.Person)
        self.assertEqual(q2, q)

        self.assertEqual(self.Person.count({'friends': chu}), 0)
        self.assertEqual(self.Person.count({'friends': adam}), 1)
        self.assertEqual(self.Person.count({'friends': josh}), 1)
        self.assertEqual(self.Person.count({'friends': {'$ne': chu}}), 4)
        self.assertEqual(self.Person.count({'friends': {'$ne': adam}}), 3)
        self.assertEqual(self.Person.count({'friends': {'$ne': josh}}), 3)
        danny.add_to_set(friends=chu)
        self.assertEquals(self.Person.count({'friends': chu}), 1)
        self.assertEquals(self.Person.count({'friends': adam}), 1)
        self.assertEquals(self.Person.count({'friends': josh}), 1)
        danny.set(friends=[adam])
        self.assertEquals(self.Person.count({'friends': josh}), 0)
        self.assertEquals(self.Person.count({'friends': chu}), 0)
        self.assertEquals(self.Person.count({'friends': adam}), 1)
        danny.push(friends=DBRef("person", chu.id))
        self.assertEquals(self.Person.count({'friends': josh}), 0)
        self.assertEquals(self.Person.count({'friends': chu}), 1)
        self.assertEquals(self.Person.count({'friends': adam}), 1)
        danny.update_one({'$pull': {'friends': josh}})
        self.assertEquals(self.Person.count({'friends': josh}), 0)
        self.assertEquals(self.Person.count({'friends': chu}), 1)
        self.assertEquals(self.Person.count({'friends': adam}), 1)
        danny.update_one({'$pull': {'friends': DBRef("person", chu.id)}})
        self.assertEquals(self.Person.count({'friends': josh}), 0)
        self.assertEquals(self.Person.count({'friends': chu}), 0)
        self.assertEquals(self.Person.count({'friends': adam}), 1)

        danny.set(friends=[DBRef("person", adam.id), josh])
        self.assertEquals(self.Person.count({'friends': josh}), 1)
        self.assertEquals(self.Person.count({'friends': chu}), 0)
        self.assertEquals(self.Person.count({'friends': adam}), 1)

        d = self.Person.find_one({'_id': danny.id})
        self.assertEquals(d.friends, [adam, josh])

    def testIdToString(self):
        u = self.Person(id=ObjectId(), some_id=ObjectId())
        u.save()
        self.assertEqual(self.Person.find_one({'id': u.id}), u)
        self.assertEqual(self.Person.find_one({'id': str(u.id)}), u)
        self.assertEqual(self.Person.find_one({'id': ObjectId()}), None)

        new_id = ObjectId()
        ret = self.Person.update_doc({'_id': str(u.id)},
                                     {'$set': {'some_id': str(new_id)}})
        self.assertEqual(ret, 1)

        p = self.Person.find_one({'id': u.id})
        self.assertEqual(p.some_id, new_id)

        self.assertEqual(self.Person.find_one({'some_id': u.some_id}), None)
        self.assertEqual(self.Person.count({'some_id': new_id}), 1)
        self.assertEqual(self.Person.count({'some_id': str(new_id)}), 1)
        p = self.Person.find_one({'some_id': new_id})
        self.assertTrue(isinstance(p.some_id, ObjectId))

        new_id2 = ObjectId()
        q = _transform_value({'$addToSet': {'id_list': str(new_id2)}},
                             self.Person)
        self.assertEqual(q['$addToSet']['id_list'], new_id2)
        ret = self.Person.update_doc({'_id': u.id},
                                     {'$addToSet': {'id_list': str(new_id2)}})
        self.assertEqual(ret, 1)
        q = _transform_value({'$addToSet': {'id_list': new_id2}}, self.Person)
        self.assertEqual(q['$addToSet']['id_list'], new_id2)

        ret = self.Person.update_doc({'_id': u.id},
                                     {'$addToSet': {'id_list': new_id2}})
        self.assertEqual(ret, 1)

        ret = self.Person.update_doc({'_id': u.id},
                                     {'$addToSet': {'id_list': new_id}})
        self.assertEqual(ret, 1)

        p = self.Person.find_one({'_id': u.id})
        self.assertEqual(len(p.id_list), 2)
        self.assertTrue(new_id in p.id_list)
        self.assertTrue(new_id2 in p.id_list)
        self.assertFalse(str(new_id2) in p.id_list)
        self.assertFalse(str(new_id) in p.id_list)

        new_id3 = ObjectId()
        new_id4 = ObjectId()
        ret = self.Person.update_doc({'_id': u.id},
                                     {'$set': {
                                         'id_list': [str(new_id3), new_id4]}})
        self.assertEqual(ret, 1)

        self.assertEqual(self.Person.count({'id_list': new_id3}), 1)
        self.assertEqual(self.Person.count({'id_list': str(new_id4)}), 1)
        q = _transform_value({'id_list': str(new_id4)}, self.Person)
        self.assertEqual(q['id_list'], new_id4)

        p = self.Person.find_one({'_id': u.id})
        self.assertEqual(p.id_list, [new_id3, new_id4])

    def testListUpdate(self):
        u = self.Person(id=ObjectId(), some_id=ObjectId())
        u.save()

        ret = self.Person.update_doc({'some_id': u.some_id},
                                     {'$set': {'some_id': u.some_id,
                                               'number_list': list(range(3))}},
                                     multi=False)
        self.assertEqual(ret, 1)
        u.reload()
        self.assertEqual(u.number_list, list(range(3)))

        ret = self.Person.update_doc({'some_id': u.some_id},
                                     {'$set': {'number_list': list(range(5))}},
                                     multi=False)
        self.assertEqual(ret, 1)
        u.reload()
        self.assertEqual(u.number_list, list(range(5)))

        ret = self.Person.update_doc({'some_id': u.some_id},
                                     {'$set': {'some_id': u.some_id,
                                               'name': 'Adam'}},
                                     multi=False)
        self.assertEqual(ret, 1)
        u.reload()
        self.assertEqual(u.name, 'Adam')

    def testPositionalOperation(self):
        red = self.Colour(name='Red')
        blue = self.Colour(name='Blue')
        green = self.Colour(name='Green')
        p = self.Person(other_colours=[red, blue, green])
        p.save()

        query = _transform_value({'$set': {'other_colours.$.name': 'Maroon'}},
                                 self.Person)
        self.assertEqual(dict(query), {'$set': {'o.$.n': 'Maroon'}})

        query = _transform_value({'other_colours.name': 'Maroon'}, self.Person)
        self.assertEqual(dict(query), {'o.n': 'Maroon'})

        p2 = self.Person.find_one({'_id': p.id, 'other_colours.name': 'Red'})
        self.assertEqual(p.id, p2.id)

        resp = self.Person.update_doc({'_id': p.id}, {
            '$set': {'other_colours.1.name': 'Aqua'}}, multi=False)
        self.assertEqual(resp, 1)

        p.reload()
        self.assertEqual(p.other_colours[0].name, 'Red')
        self.assertEqual(p.other_colours[1].name, 'Aqua')
        self.assertEqual(p.other_colours[2].name, 'Green')

        resp = self.Person.update_doc(
            {'_id': p.id, 'other_colours.name': 'Red'},
            {'$set': {'other_colours.$.name': 'Maroon'}}, multi=False)
        self.assertEqual(resp, 1)

        p.reload()
        self.assertEqual(p.other_colours[0].name, "Maroon")
        self.assertEqual(p.other_colours[1].name, "Aqua")
        self.assertEqual(p.other_colours[2].name, "Green")

    def testRemove(self):
        adam = self.Person(name="Adam")
        adam.save()
        josh = self.Person(name="Josh")
        josh.save()
        chu = self.Person(name="Chu")
        chu.save()
        danny = self.Person(name="Danny", friends=[adam, josh])
        danny.save()

        self.assertEqual(self.Person.count({}), 4)
        self.Person.remove({'name': {'$in': ['Adam', 'Josh']}})
        self.assertEqual(self.Person.count({}), 2)
        self.assertEqual(self.Person.count({'name': 'Adam'}), 0)

    def testAddToSet2(self):
        adam = self.Person(name="Adam")
        adam.save()
        red = self.Colour(name='Red')
        blue = self.Colour(name='Blue')
        green = self.Colour(name='Green')
        adam.add_to_set(other_colours=red)
        self.assertEquals(adam.other_colours, [red])
        adam.add_to_set(other_colours=red)
        self.assertEquals(adam.other_colours, [red])
        adam.add_to_set(other_colours=blue)
        self.assertEquals(adam.other_colours, [red, blue])
        adam.update_one(
            {'$addToSet': {'other_colours': {'$each': [red, green, blue]}}})
        self.assertEquals(adam.other_colours, [red, blue, green])

    def testEmptyUpdates(self):
        adam = self.Person(name='Adam')
        adam.save()

        self.assertRaises(ValueError, adam.update_one, {})
        self.assertRaises(ValueError, self.Person.update_doc, {'name': 'Adam'},
                          {})

        adam.reload()
        self.assertEqual(adam.name, 'Adam')

    def testDictQueries(self):
        adam = self.Person(name='Adam', arbitrary_dict={'likes': 'boats'})
        adam.save()
        josh = self.Person(name="Josh", arbitrary_dict={'likes': 'fishing'})
        josh.save()

        p = self.Person.find({'arbitrary_dict.likes': 'boats'})
        self.assertEquals(len(p), 1)
        self.assertEquals(p[0].name, "Adam")

        p = self.Person.find({'arbitrary_dict.likes': 'fishing'})
        self.assertEquals(len(p), 1)
        self.assertEquals(p[0].name, "Josh")

        p = self.Person.find({'arbitrary_dict.likes': 'boring stuff'})
        self.assertEquals(len(p), 0)

        p = self.Person.find({'arbitrary_dict.hates': 'the world'})
        self.assertEquals(len(p), 0)

    def testList(self):
        adam = self.Person(name='Adam', number_list=[1, 2, 3])
        adam.save()

        self.assertEquals(self.Person.count({'number_list': [1, 2, 3]}), 1)
        self.assertEquals(self.Person.count({'number_list': 1}), 1)
        self.assertEquals(self.Person.count({'number_list': 4}), 0)
        self.assertEquals(self.Person.count({'number_list': 2}), 1)
        self.assertEquals(self.Person.count({'number_list': [1, 2, 3, 4]}), 0)
        self.assertEquals(self.Person.count({'number_list': [1, 3, 2]}), 0)
        self.assertEquals(self.Person.count({'number_list': [1, 2]}), 0)

    # def testFindAndModify(self):
    #     adam = self.Person(name="Adam", age=23)
    #     adam.save()
    #     danny = self.Person(name="Danny", age=30)
    #     danny.save()
    #
    #     res = self.Person._get_collection().find_and_modify({"name": "Adam"},
    #                                                         {"$inc": {
    #                                                             "age": 1}})
    #     res2 = self.Person.find_one({"name": "Adam"})
    #
    #     # new_adam = self.Person.modify({"name": "Adam"})
    #     # adam = self.Person.find_and_modify({"name": "Adam"},
    #     #                                    {"$inc": {"age": 1}})
    #     # self.assertEqual(adam.age, 23)
    #     # adam.reload()
    #     # self.assertEqual(adam.age, 24)

    def testDistinct(self):
        pass

    def testPushSlice(self):
        adam = self.Person(name='Adam', number_list=list(range(50)))
        adam.save()

        adam.update_one(
            {'$push': {'number_list': {'$each': [50, 51, 52], '$slice': -20}}})
        adam.reload()
        self.assertEqual(adam.number_list, list(range(33, 53)))
        self.assertEqual(len(adam.number_list), 20)

        adam = self.Person(name='Adam', number_list=list(range(50)))
        adam.save()

        adam.update_one(
            {'$push': {'number_list': {'$each': [50, 51, 52], '$slice': -100}}})
        adam.reload()
        self.assertEqual(adam.number_list, list(range(53)))
        self.assertEqual(len(adam.number_list), 53)

    def testPushSliceEmbedded(self):
        blue = self.Colour(name="Blue")
        green = self.Colour(name="Green")
        red = self.Colour(name="Red")
        adam = self.Person(name="Adam", other_colours=[blue, green])
        adam.save()

        adam.update_one(
            {'$push': {'other_colours': {'$each': [red], '$slice': -2}}})
        adam.reload()
        self.assertEqual(adam.other_colours, [green, red])

        adam = self.Person(name="Adam", other_colours=[blue, green])
        adam.save()

        adam.update_one(
            {"$push": {"other_colours": {"$each": [red], "$slice": -5}}})
        adam.reload()
        self.assertEquals(adam.other_colours, [blue, green, red])

    def testToMongoReference(self):
        pass

    def testTransformHint(self):
        self.assertEqual(
            _transform_hint(self.Person, [("age", 1)]), [("a", 1)])

        self.assertEqual(
            _transform_hint(self.Person, [("age", 1), ("name", 1)]),
            [("a", 1), ("name", 1)])

        self.assertEqual(_transform_hint(self.Person, []), [])

        self.assertEqual(_transform_hint(self.Person, [("_id", 1)]),
                         [("_id", 1)])

        self.assertEqual(
            _transform_hint(self.Person, [("age", 1), ("gender", 1)]),
            [("a", 1), ("g", 1)])

        self.assertEqual(_transform_hint(self.Person,
                                         [("age", 1),
                                          ("favourite_colour.name", 1)]),
                         [("a", 1), ("c.n", 1)])

        self.assertEqual(_transform_hint(self.Person,
                                         [("age", 1),
                                          ("other_colours.name", 1)]),
                         [("a", 1), ("o.n", 1)])

    def testOHintNotChanged(self):
        hint = [("age", 1), ("favourite_colour.name", 1)]
        self.assertEqual(
            _transform_hint(self.Person, hint),
            [("a", 1), ("c.n", 1)])

        self.assertEqual(hint, [("age", 1), ("favourite_colour.name", 1)])

    def test_can_set_reference_field_with_dbref(self):
        user_id = ObjectId()
        user = self.User(id=user_id)
        user.save()

        person = self.Person(name='Hydra', user=DBRef(u'user', user_id))

        self.assertEqual(person.user, user)

        person.save()

        person_loaded = self.Person.find_one({'name': 'Hydra'})
        self.assertEqual(person_loaded.user, user)

    def test_can_set_reference_field_list_with_dbrefs(self):
        friend_1 = self.Person()
        friend_2 = self.Person()
        friend_1.save()
        friend_2.save()

        person = self.Person(name='Dagon',
                             friends=[DBRef(u'person', friend_1.id),
                                      DBRef(u'person', friend_2.id)])

        self.assertIn(friend_1, person.friends)
        self.assertIn(friend_2, person.friends)

        person.save()

        person_loaded = self.Person.find_one({'name': 'Dagon'})
        self.assertIn(friend_1, person_loaded.friends)
        self.assertIn(friend_2, person_loaded.friends)


class BulkOperationTest(unittest.TestCase):
    def setUp(self):
        connect()
        self.db = _get_db()
        mongoengine.base._document_registry = {}

        class Person(Document, MongoOperation):
            name = StringField()
            age = IntField(default=20)

        self.person_cls = Person

    def tearDown(self) -> None:
        self.person_cls.drop_collection()

    @contextlib.contextmanager
    def assertWarns(self, warning_type=UserWarning):
        with warnings.catch_warnings(record=True) as warning_list:
            yield

            self.assertTrue(
                any(_.category == warning_type for _ in warning_list),
                '%s not emitted' % warning_type.__name__
            )

    @contextlib.contextmanager
    def assertDoesNotWarn(self):
        with warnings.catch_warnings(record=True) as warning_list:
            yield

            self.assertFalse(
                warning_list,
                'Warnings unexpectedly emitted: %s' % warning_list
            )

    def test_can_bulk_insert(self):
        names = ['Michael', 'Joel', 'Austin']
        with self.person_cls.bulk():
            for name in names:
                person = self.person_cls(name=name)
                person.bulk_save()
        for name in names:
            self.assertIsNotNone(self.person_cls.find_one({'name': name}))

    def test_failure_raises(self):
        p_id = ObjectId()
        person = self.person_cls(id=p_id, name='Kelly')
        person.save()
        with self.assertRaises(BulkOperationError):
            with self.person_cls.bulk():
                bad_person = self.person_cls(id=p_id, name='K2')
                bad_person.bulk_save()

    def test_failure_partially_updates(self):
        person = self.person_cls(name='Patrick')
        person.save(validate=False)
        new_people = [
            self.person_cls(name='David'),
            self.person_cls(name='P2'),
        ]
        person._pymongo().update(
            {'name': 'Patrick'},
            {'$set': {'age': None}}
        )

        with self.assertRaises(BulkOperationError) as r:
            with self.person_cls.bulk():
                new_people[0].bulk_save()
                self.person_cls.bulk_update(
                    {'name': 'Patrick'},
                    {'$inc': {'age': 1}},
                )
                new_people[1].bulk_save()
        e = r.exception
        self.assertEqual(e.index, 1)

        self.assertIsNotNone(new_people[0].id)
        self.assertIsNotNone(new_people[1].id)

        david = self.person_cls.find_one({'name': 'David'})
        self.assertEqual(david.id, new_people[0].id)

    def test_update_multi(self):
        person_s = self.person_cls(name='Sorey')
        person_s.save()
        person_j = self.person_cls(name='Jenna')
        person_j.save()
        with self.person_cls.bulk():
            self.person_cls.bulk_update(
                {'name': 'Sorey'}, {'$set': {'age': 20}}
            )
            self.person_cls.bulk_update(
                {'name': 'Jenna'}, {'$set': {'age': 21}}
            )

        person_s.reload()
        person_j.reload()

        self.assertEqual(person_s.age, 20)
        self.assertEqual(person_j.age, 21)

    def test_update_and_insert(self):
        person = self.person_cls(name='Lyla')
        person.save()

        with self.person_cls.bulk():
            self.person_cls.bulk_update(
                {'name': 'Lyla'}, {'$set': {'age': 30}}
            )
            new_person = self.person_cls(name='Kyle')
            new_person.bulk_save()

        person.reload()

        self.assertEqual(person.age, 30)
        self.assertIsNotNone(new_person.id)

    def test_cannot_bulk_update_outside_bulk(self):
        with self.assertRaises(RuntimeError):
            self.person_cls.bulk_update(
                {'name': 'Bad'}, {'$set': {'age': 99}}
            )

        person = self.person_cls(name='Good')
        with self.person_cls.bulk():
            person.bulk_save()

        with self.assertRaises(RuntimeError):
            self.person_cls.bulk_update(
                {'name': 'Bad'}, {'$set': {'age': 99}}
            )

    def test_cannot_bulk_insert_outside_bulk(self):
        person = self.person_cls(name='Bad')
        with self.assertRaises(RuntimeError):
            person.bulk_save()

        ok_person = self.person_cls(name='Better')
        with self.person_cls.bulk():
            ok_person.bulk_save()

        with self.assertRaises(RuntimeError):
            person.bulk_save()

    def test_cannot_nest_bulk_insert_blocks(self):
        with self.person_cls.bulk(allow_empty=True):
            with self.assertRaises(RuntimeError):
                with self.person_cls.bulk():
                    pass

    def test_empty_bulk_op_warns(self):
        with self.assertWarns():
            with self.person_cls.bulk():
                pass

    def test_empty_bulk_op_not_allowed(self):
        with self.assertRaises(pymongo.errors.InvalidOperation):
            with self.person_cls.bulk(allow_empty=False):
                pass

    def test_empty_bulk_op_allowed(self):
        with self.assertDoesNotWarn():
            with self.person_cls.bulk(allow_empty=True):
                pass


if __name__ == "__main__":
    unittest.main()
