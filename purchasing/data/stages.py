# -*- coding: utf-8 -*-

from sqlalchemy.orm import backref

from purchasing.database import db, Model, Column, ReferenceCol
from purchasing.data.contract_stages import ContractStage
from purchasing.data.contracts import ContractBase

class Stage(Model):
    __tablename__ = 'stage'

    id = Column(db.Integer, primary_key=True, index=True)
    name = Column(db.String(255))
    post_opportunities = Column(db.Boolean, default=False, nullable=False)

    default_message = Column(db.Text)

    def __unicode__(self):
        return self.name

    @classmethod
    def choices_factory(cls):
        return [(i.id, i.name) for i in cls.query.all()]

class StageProperty(Model):
    __tablename__ = 'stage_property'

    id = Column(db.Integer, primary_key=True, index=True)
    stage = db.relationship('Stage', backref=backref(
        'properties', lazy='dynamic', cascade='all, delete-orphan'
    ))
    stage_id = ReferenceCol('stage', ondelete='CASCADE')
    key = Column(db.String(255), nullable=False)
    value = Column(db.String(255))

    def __unicode__(self):
        return '{key}: {value}'.format(key=self.key, value=self.value)

def get_contract_stages(contract):
    '''Returns the appropriate stages and their metadata based on a contract id
    '''
    return db.session.query(
        ContractStage.contract_id, ContractStage.stage_id, ContractStage.id,
        ContractStage.entered, ContractStage.exited, Stage.name, Stage.default_message,
        Stage.post_opportunities, ContractBase.description, Stage.id.label('stage_id'),
        (db.func.extract(db.text('DAYS'), ContractStage.exited - ContractStage.entered)).label('days_spent'),
        (db.func.extract(db.text('HOURS'), ContractStage.exited - ContractStage.entered)).label('hours_spent')
    ).join(Stage, Stage.id == ContractStage.stage_id).join(
        ContractBase, ContractBase.id == ContractStage.contract_id
    ).filter(
        ContractStage.contract_id == contract.id,
        ContractStage.flow_id == contract.flow_id
    ).order_by(ContractStage.id).all()
