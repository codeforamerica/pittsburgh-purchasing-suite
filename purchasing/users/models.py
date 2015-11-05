# -*- coding: utf-8 -*-
from flask.ext.login import UserMixin, AnonymousUserMixin

from purchasing.database import Column, db, Model, ReferenceCol, SurrogatePK
from sqlalchemy.orm import backref

class Role(SurrogatePK, Model):
    '''Model to handle view-based permissions

    Attributes:
        id: primary key
        name: role name
    '''
    __tablename__ = 'roles'
    name = Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return '<Role({name})>'.format(name=self.name)

    def __unicode__(self):
        return self.name

    @classmethod
    def query_factory(cls):
        '''Generates a query of all roles

        Returns:
            `sqla query`_ of all roles
        '''
        return cls.query

    @classmethod
    def no_admins(cls):
        '''Generates a query of non-admin roles

        Returns:
            `sqla query`_ of roles without administrative access
        '''
        return cls.query.filter(cls.name != 'superadmin')

class User(UserMixin, SurrogatePK, Model):
    '''User model

    Attributes:
        id: primary key
        email: user email address
        first_name: first name of user
        last_name: last name of user
        active: whether user is currently active or not
        role_id: foreign key of user's role
        role: relationship of user to role table
        department_id: foreign key of user's department
        department: relationship of user to department table
    '''

    __tablename__ = 'users'
    email = Column(db.String(80), unique=True, nullable=False, index=True)
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
        '''Build full name of user

        Returns:
            concatenated string of first_name and last_name values
        '''
        return "{0} {1}".format(self.first_name, self.last_name)

    def __repr__(self):
        return '<User({email!r})>'.format(email=self.email)

    def __unicode__(self):
        return self.email

    def get_following(self):
        '''Generate user contract subscriptions

        Returns:
            list of ids for contracts followed by user
        '''
        return [i.id for i in self.contracts_following]

    def is_conductor(self):
        '''Check if user can access conductor application

        Returns:
            True if user's role is either conductor, admin, or superadmin,
            False otherwise
        '''
        return self.role.name in ('conductor', 'admin', 'superadmin')

    def print_pretty_name(self):
        '''Generate long version text representation of user

        Returns:
            full_name if first_name and last_name exist, email otherwise
        '''
        if self.first_name and self.last_name:
            return self.full_name
        else:
            return self.email

    def print_pretty_first_name(self):
        '''Generate abbreviated text representation of user

        Returns:
            first_name if first_name exists,
            `localpart <https://en.wikipedia.org/wiki/Email_address#Local_part>`_
            otherwise
        '''
        if self.first_name:
            return self.first_name
        else:
            return self.email.split('@')[0]

    @classmethod
    def conductor_users_query(cls):
        '''Query users with access to conductor

        Returns:
            list of users with ``is_conductor`` value of True
        '''
        return [i for i in cls.query.all() if i.is_conductor()]


class Department(SurrogatePK, Model):
    '''Department model

    Attributes:
        Name of department
    '''
    __tablename__ = 'department'

    name = Column(db.String(255), nullable=False, unique=True)

    def __unicode__(self):
        return self.name

    @classmethod
    def query_factory(cls):
        '''Generate a department query factory.

        Returns:
            Department query with new users filtered out
        '''
        return cls.query.filter(cls.name != 'New User')

    @classmethod
    def get_dept(cls, dept_name):
        '''Query Department by name.

        Arguments:
            dept_name: name used for query

        Returns:
            an instance of Department
        '''
        return cls.query.filter(db.func.lower(cls.name) == dept_name.lower()).first()

    @classmethod
    def choices(cls, blank=False):
        '''Query available departments by name and id.

        Arguments:
            blank: adds none choice to list when True,
                only returns Departments when False. Defaults to False.

        Returns:
            list of (department id, department name) tuples
        '''
        departments = [(i.id, i.name) for i in cls.query_factory().all()]
        if blank:
            departments = [(None, '-----')] + departments
        return departments

class AnonymousUser(AnonymousUserMixin):
    '''Custom mixin for handling anonymous (non-logged-in) users

    Attributes:
        role: :py:class:`~purchasing.user.models.Role`
            object with name set to 'anonymous'
        department: :py:class:`~purchasing.user.models.Department`
            object with name set to 'anonymous'
        id: Defaults to -1

    See Also:
        ``AnonymousUser`` subclasses the `flask_login anonymous user mixin
        <https://flask-login.readthedocs.org/en/latest/#anonymous-users>`_,
        which contains a number of class and instance methods around
        determining if users are currently logged in.
    '''
    role = Role(name='anonymous')
    department = Department(name='anonymous')
    id = -1

    def __init__(self, *args, **kwargs):
        super(AnonymousUser, self).__init__(*args, **kwargs)
