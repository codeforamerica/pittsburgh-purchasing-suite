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

DEPARTMENT_CHOICES = [
    (None, '-----'),
    ('Bureau of Neighborhood Empowerment', 'Bureau of Neighborhood Empowerment'),
    ('Citizen Police Review Board', 'Citizen Police Review Board'),
    ("City Clerk's Office", "City Clerk's Office"),
    ('City Controller', 'City Controller'),
    ('City Council', 'City Council'),
    ('Commission on Human Relations', 'Commission on Human Relations'),
    ('Department of City Planning', 'Department of City Planning'),
    ('Department of Finance', 'Department of Finance'),
    ('Department of Law', 'Department of Law'),
    ('Department of Parks and Recreation', 'Department of Parks and Recreation'),
    ('Department of Permits, Licenses, and Inspections', 'Department of Permits, Licenses, and Inspections'),
    ('Department of Public Safety', 'Department of Public Safety'),
    ('Department of Public Works', 'Department of Public Works'),
    ('Ethics Board', 'Ethics Board'),
    ('Innovation and Performance', 'Innovation and Performance'),
    ('Office of Management and Budget', 'Office of Management and Budget'),
    ('Office of Municipal Investigations', 'Office of Municipal Investigations'),
    ('Office of the Mayor', 'Office of the Mayor'),
    ('Personnel and Civil Service Commission', 'Personnel and Civil Service Commission'),
    ('Other', 'Other')
]

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
    department = Column(db.String(255), nullable=False)
    active = Column(db.Boolean(), default=True)
    role_id = ReferenceCol('roles', ondelete='SET NULL', nullable=True)

    @property
    def full_name(self):
        return "{0} {1}".format(self.first_name, self.last_name)

    def __repr__(self):
        return '<User({email!r})>'.format(email=self.email)

    def __unicode__(self):
        return self.email

    def get_starred(self):
        return [i.id for i in self.contracts_starred]

    def get_following(self):
        return [i.id for i in self.contracts_following]

    def is_conductor(self):
        return self.role.name in ('conductor', 'admin', 'superadmin')

class AnonymousUser(AnonymousUserMixin):
    role = {'name': 'anonymous'}
    id = -1
