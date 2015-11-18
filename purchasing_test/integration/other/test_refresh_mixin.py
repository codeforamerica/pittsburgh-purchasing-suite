# -*- coding: utf-8 -*-

from purchasing.database import Model, RefreshSearchViewMixin, Column
from purchasing.app import db

from purchasing_test.test_base import BaseTestCase

class FakeModel(RefreshSearchViewMixin, Model):
    __tablename__ = 'fakefake'
    __table_args__ = {'extend_existing': True}

    id = Column(db.Integer, primary_key=True)
    description = Column(db.String(255))

    def __init__(self, *args, **kwargs):
        super(FakeModel, self).__init__(*args, **kwargs)

    @classmethod
    def record_called(cls):
        cls.called = True

    @classmethod
    def reset_called(cls):
        cls.called = False

    @classmethod
    def event_handler(cls, *args, **kwargs):
        return cls.record_called()

class TestEventHandler(BaseTestCase):
    def setUp(self):
        super(TestEventHandler, self).setUp()
        FakeModel.reset_called()

    def test_init(self):
        self.assertFalse(FakeModel.called)

    def test_create(self):
        FakeModel.create(description='abcd')
        self.assertTrue(FakeModel.called)

    def test_update(self):
        fake_model = FakeModel.create(description='abcd')
        FakeModel.reset_called()
        self.assertFalse(FakeModel.called)
        fake_model.update(description='efgh')
        self.assertTrue(FakeModel.called)

    def test_delete(self):
        fake_model = FakeModel.create(description='abcd')
        FakeModel.reset_called()
        self.assertFalse(FakeModel.called)
        fake_model.delete()
        self.assertTrue(FakeModel.called)
