# -*- coding: utf-8 -*-
import datetime as dt

from flask.ext.login import UserMixin, AnonymousUserMixin

from purchasing.database import (
    Column,
    db,
    Model,
    ReferenceCol,
    relationship,
    SurrogatePK,
)

class Role(SurrogatePK, Model):
    __tablename__ = 'roles'
    name = Column(db.String(80), unique=True, nullable=False)
    users = db.relationship('User', lazy='dynamic', backref='role')

    def __init__(self, name):
        db.Model.__init__(self, name=name)

    def __repr__(self):
        return '<Role({name})>'.format(name=self.name)

    def __unicode__(self):
        return self.name

class User(UserMixin, SurrogatePK, Model):

    __tablename__ = 'users'
    email = Column(db.String(80), unique=True, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    first_name = Column(db.String(30), nullable=True)
    last_name = Column(db.String(30), nullable=True)
    active = Column(db.Boolean(), default=False)
    role_id = ReferenceCol('roles', ondelete='SET NULL', nullable=True)

    def __init__(self, email, **kwargs):
        db.Model.__init__(self, email=email, **kwargs)

    @property
    def full_name(self):
        return "{0} {1}".format(self.first_name, self.last_name)

    def __repr__(self):
        return '<User({email!r})>'.format(email=self.email)

    def __unicode__(self):
        return self.email

class AnonymousUser(AnonymousUserMixin):
    role = {'name': 'anonymous'}
