# -*- coding: utf-8 -*-
import datetime as dt

from flask.ext.login import UserMixin, AnonymousUserMixin

from purchasing.database import Column, db, Model, ReferenceCol, SurrogatePK
from sqlalchemy.orm import backref

class Role(SurrogatePK, Model):
    __tablename__ = 'roles'
    name = Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return '<Role({name})>'.format(name=self.name)

    def __unicode__(self):
        return self.name

    @classmethod
    def query_factory(cls):
        return cls.query

    @classmethod
    def no_admins(cls):
        return cls.query.filter(~cls.name.in_(['superadmin', 'admin']))

class User(UserMixin, SurrogatePK, Model):

    __tablename__ = 'users'
    email = Column(db.String(80), unique=True, nullable=False, index=True)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    first_name = Column(db.String(30), nullable=True)
    last_name = Column(db.String(30), nullable=True)
    active = Column(db.Boolean(), default=True)

    role_id = ReferenceCol('roles', ondelete='SET NULL', nullable=True)
    role = db.relationship(
        'Role', backref=backref('users', lazy='dynamic'),
        foreign_keys=role_id, primaryjoin='User.role_id==Role.id'
    )

    department_id = ReferenceCol('department', ondelete='SET NULL', nullable=True)
    department = db.relationship(
        'Department', backref=backref('users', lazy='dynamic'),
        foreign_keys=department_id, primaryjoin='User.department_id==Department.id'
    )

    @property
    def full_name(self):
        return "{0} {1}".format(self.first_name, self.last_name)

    def __repr__(self):
        return '<User({email!r})>'.format(email=self.email)

    def __unicode__(self):
        return self.email

    def get_following(self):
        return [i.id for i in self.contracts_following]

    def is_conductor(self):
        return self.role.name in ('conductor', 'admin', 'superadmin')

    def print_pretty_name(self):
        if self.first_name and self.last_name:
            return self.full_name
        else:
            return self.email

    def print_pretty_first_name(self):
        if self.first_name:
            return self.first_name
        else:
            return self.email.split('@')[0]

    @classmethod
    def conductor_users_query(cls):
        return [i for i in cls.query.all() if i.is_conductor()]


class Department(SurrogatePK, Model):
    __tablename__ = 'department'

    name = Column(db.String(255), nullable=False, unique=True)

    def __unicode__(self):
        return self.name

    @classmethod
    def query_factory(cls):
        return cls.query.filter(cls.name != 'New User')

    @classmethod
    def choices(cls, blank=False):
        departments = [(i.id, i.name) for i in cls.query_factory().all()]
        if blank:
            departments = [(None, '-----')] + departments
        return departments

class AnonymousUser(AnonymousUserMixin):
    role = Role(name='anonymous')
    department = Department(name='anonymous')
    id = -1
