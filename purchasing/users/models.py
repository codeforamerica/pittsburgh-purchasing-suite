# -*- coding: utf-8 -*-
import datetime as dt

from flask.ext.login import UserMixin, AnonymousUserMixin

from purchasing.database import (
    Column,
    db,
    Model,
    ReferenceCol,
    SurrogatePK,
)

class Role(SurrogatePK, Model):
    __tablename__ = 'roles'
    name = Column(db.String(80), unique=True, nullable=False)
    users = db.relationship('User', lazy='dynamic', backref='role')

    def __repr__(self):
        return '<Role({name})>'.format(name=self.name)

    def __unicode__(self):
        return self.name

class User(UserMixin, SurrogatePK, Model):

    __tablename__ = 'users'
    email = Column(db.String(80), unique=True, nullable=False, index=True)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    first_name = Column(db.String(30), nullable=True)
    last_name = Column(db.String(30), nullable=True)
    department_id = ReferenceCol('department', ondelete='SET NULL', nullable=True)
    active = Column(db.Boolean(), default=True)
    role_id = ReferenceCol('roles', ondelete='SET NULL', nullable=True)

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

class Department(SurrogatePK, Model):
    __tablename__ = 'department'

    users = db.relationship('User', lazy='dynamic', backref='department')
    name = Column(db.String(255), nullable=False, unique=True)

    def __unicode__(self):
        return self.name

class AnonymousUser(AnonymousUserMixin):
    role = Role(name='anonymous')
    department = Department(name='anonymous')
    id = -1

def department_query():
    return Department.query.filter(Department.name != 'New User')

def get_department_choices(blank=False):
    departments = [(i.id, i.name) for i in department_query().all()]
    if blank:
        departments = [(None, '-----')] + departments
    return departments
