# -*- coding: utf-8 -*-

import datetime
from purchasing.database import (
    Column,
    Model,
    db,
    ReferenceCol,
)
from sqlalchemy.dialects.postgres import ARRAY
from sqlalchemy.schema import Table
from sqlalchemy.orm import backref

company_contract_association_table = Table(
    'company_contract_association', Model.metadata,
    Column('company_id', db.Integer, db.ForeignKey('company.id')),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id')),
)

contract_user_association_table = Table(
    'contract_user_association', Model.metadata,
    Column('user_id', db.Integer, db.ForeignKey('users.id')),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id')),
)

class Company(Model):
    __tablename__ = 'company'

    id = Column(db.Integer, primary_key=True)
    company_name = Column(db.String(255), nullable=False, unique=True)
    contact_first_name = Column(db.String(255))
    contact_last_name = Column(db.String(255))
    contact_addr1 = Column(db.String(255))
    contact_addr2 = Column(db.String(255))
    contact_city = Column(db.String(255))
    contact_state = Column(db.String(255))
    contact_zip = Column(db.Integer)
    contact_phone = Column(db.String(255))
    contact_email = Column(db.String(255))
    contracts = db.relationship(
        'ContractBase',
        secondary=company_contract_association_table,
        backref='companies'
    )

    def __unicode__(self):
        return self.company_name

class ContractBase(Model):
    __tablename__ = 'contract'

    id = Column(db.Integer, primary_key=True)
    created_at = Column(db.DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(db.DateTime, default=datetime.datetime.utcnow())
    contract_type = Column(db.String(255))
    expiration_date = Column(db.Date)
    description = Column(db.Text)
    current_stage = db.relationship('Stage', lazy='subquery')
    current_stage_id = ReferenceCol('stage', ondelete='SET NULL', nullable=True)
    current_flow = db.relationship('Flow', lazy='subquery')
    flow_id = ReferenceCol('flow', ondelete='SET NULL', nullable=True)
    users = db.relationship(
        'User',
        secondary=contract_user_association_table,
        backref='contracts_following'
    )

    def __unicode__(self):
        return self.description

class ContractProperty(Model):
    __tablename__ = 'contract_property'

    id = Column(db.Integer, primary_key=True)
    contract = db.relationship('ContractBase', backref=backref(
        'properties', lazy='dynamic', cascade='save-update, delete'
    ))
    contract_id = ReferenceCol('contract', ondelete='CASCADE')
    key = Column(db.String(255), nullable=False)
    value = Column(db.String(255))

    def __unicode__(self):
        return '{key}: {value}'.format(key=self.key, value=self.value)

# class ContractAudit(Model):
#     __tablename__ = 'contract_audit'

class Stage(Model):
    __tablename__ = 'stage'

    id = Column(db.Integer, primary_key=True)
    contract = db.relationship('ContractBase', backref='stage_id', lazy='subquery')
    name = Column(db.String(255))

    def __unicode__(self):
        return self.name

class StageProperty(Model):
    __tablename__ = 'stage_property'

    id = Column(db.Integer, primary_key=True)
    stage = db.relationship('Stage', backref=backref(
        'properties', lazy='dynamic', cascade='save-update, delete'
    ))
    stage_id = ReferenceCol('stage', ondelete='CASCADE')
    key = Column(db.String(255), nullable=False)
    value = Column(db.String(255))

    def __unicode__(self):
        return '{key}: {value}'.format(key=self.key, value=self.value)

class Flow(Model):
    __tablename__ = 'flow'

    id = Column(db.Integer, primary_key=True)
    flow_name = Column(db.Text, unique=True)
    contract = db.relationship('ContractBase', backref='flow', lazy='subquery')
    stage_order = Column(ARRAY(db.Integer))

    def __unicode__(self):
        return self.flow_name
