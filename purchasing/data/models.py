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
    current_stage = ReferenceCol('stage', nullable=True)
    flow = ReferenceCol('flow', nullable=True)
    contract_properties = db.relationship('ContractProperty', lazy='dynamic', passive_deletes=True)

class ContractProperty(Model):
    __tablename__ = 'contract_property'

    id = Column(db.Integer, primary_key=True)
    contract = ReferenceCol('contract', ondelete='CASCADE')
    key = Column(db.String(255))
    value = Column(db.String(255))

# class ContractAudit(Model):
#     __tablename__ = 'contract_audit'

class Stage(Model):
    __tablename__ = 'stage'

    id = Column(db.Integer, primary_key=True)
    stage_property = db.relationship('StageProperty', lazy='dynamic')
    contract = db.relationship('ContractBase', backref='stage_id', lazy='subquery', passive_deletes=True)
    name = Column(db.String(255))

class StageProperty(Model):
    __tablename__ = 'stage_property'

    id = Column(db.Integer, primary_key=True)
    stage = ReferenceCol('stage', ondelete='CASCADE')
    property = Column(db.Text)

class Flow(Model):
    __tablename__ = 'flow'

    id = Column(db.Integer, primary_key=True)
    flow_name = Column(db.Text, unique=True)
    contract = db.relationship('ContractBase', backref='flow_id', lazy='subquery')
    stage_order = Column(ARRAY(db.Integer))
