# -*- coding: utf-8 -*-

import datetime
from purchasing.database import (
    Column,
    Model,
    db,
    ReferenceCol,
)
from sqlalchemy.dialects.postgres import ARRAY

class ContractBase(Model):
    __tablename__ = 'contract'

    id = Column(db.Integer, primary_key=True)
    created_at = Column(db.DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(db.DateTime, default=datetime.datetime.utcnow())
    contract_type = Column(db.String(255))
    description = Column(db.Text)
    current_stage = db.relationship('Stage', lazy='subquery')
    current_stage_id = ReferenceCol('stage', ondelete='SET NULL', nullable=True)
    current_flow = db.relationship('Flow', lazy='subquery')
    flow_id = ReferenceCol('flow', ondelete='SET NULL', nullable=True)
    contract_properties = db.relationship('ContractProperty', lazy='dynamic')

    def __unicode__(self):
        return self.description

class ContractProperty(Model):
    __tablename__ = 'contract_property'

    id = Column(db.Integer, primary_key=True)
    contract = db.relationship('ContractBase', backref='contract')
    contract_id = ReferenceCol('contract', ondelete='CASCADE')
    key = Column(db.String(255))
    value = Column(db.String(255))

    def __unicode__(self):
        return '{key}: {value}'.format(key=self.key, value=self.value)

# class ContractAudit(Model):
#     __tablename__ = 'contract_audit'

class Stage(Model):
    __tablename__ = 'stage'

    id = Column(db.Integer, primary_key=True)
    stage_property = db.relationship('StageProperty', lazy='dynamic', cascade='delete')
    contract = db.relationship('ContractBase', backref='stage_id', lazy='subquery')
    name = Column(db.String(255))

    def __unicode__(self):
        return self.name

class StageProperty(Model):
    __tablename__ = 'stage_property'

    id = Column(db.Integer, primary_key=True)
    stage = db.relationship('Stage', backref='stage')
    stage_id = ReferenceCol('stage', ondelete='CASCADE')
    key = Column(db.String(255))
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
