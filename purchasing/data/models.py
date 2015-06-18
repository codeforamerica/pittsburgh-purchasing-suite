# -*- coding: utf-8 -*-

import datetime
from purchasing.database import (
    Column,
    Model,
    db,
    ReferenceCol
)
from sqlalchemy.dialects.postgres import ARRAY
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.schema import Table, Sequence
from sqlalchemy.orm import backref

company_contract_association_table = Table(
    'company_contract_association', Model.metadata,
    Column('company_id', db.Integer, db.ForeignKey('company.id', ondelete='SET NULL'), index=True),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id', ondelete='SET NULL'), index=True),
)

contract_user_association_table = Table(
    'contract_user_association', Model.metadata,
    Column('user_id', db.Integer, db.ForeignKey('users.id'), index=True),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id'), index=True),
)

contract_starred_association_table = Table(
    'contract_starred_association', Model.metadata,
    Column('user_id', db.Integer, db.ForeignKey('users.id'), index=True),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id'), index=True),
)

class SearchView(Model):
    '''search_view is a materialized view with all of our text columns
    '''
    __tablename__ = 'search_view'

    id = Column(db.Text, primary_key=True, index=True)
    contract_id = Column(db.Integer)
    company_id = Column(db.Integer)
    financial_id = Column(db.Integer)
    expiration_date = Column(db.Date)
    contract_description = Column(db.Text)
    tsv_contract_description = Column(TSVECTOR)
    company_name = Column(db.Text)
    tsv_company_name = Column(TSVECTOR)
    detail_key = Column(db.Text)
    detail_value = Column(db.Text)
    tsv_detail_value = Column(TSVECTOR)
    line_item_description = Column(db.Text)
    tsv_line_item_description = Column(TSVECTOR)

class Company(Model):
    __tablename__ = 'company'

    id = Column(db.Integer, primary_key=True, index=True)
    company_name = Column(db.String(255), nullable=False, unique=True, index=True)
    contracts = db.relationship(
        'ContractBase',
        secondary=company_contract_association_table,
        backref='companies',
    )

    def __unicode__(self):
        return self.company_name

class CompanyContact(Model):
    __tablename__ = 'company_contact'

    id = Column(db.Integer, primary_key=True, index=True)
    company = db.relationship(
        'Company',
        backref=backref('contacts', lazy='dynamic', cascade='all, delete-orphan')
    )
    company_id = ReferenceCol('company', ondelete='cascade')
    first_name = Column(db.String(255))
    last_name = Column(db.String(255))
    addr1 = Column(db.String(255))
    addr2 = Column(db.String(255))
    city = Column(db.String(255))
    state = Column(db.String(255))
    zip_code = Column(db.Integer)
    phone_number = Column(db.String(255))
    fax_number = Column(db.String(255))
    email = Column(db.String(255))

    def __unicode__(self):
        return '{first} {last} - {email}'.format(
            first=self.first_name, last=self.last_name,
            email=self.email
        )

class ContractBase(Model):
    __tablename__ = 'contract'

    id = Column(db.Integer, primary_key=True)
    financial_id = Column(db.Integer)
    created_at = Column(db.DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(db.DateTime, default=datetime.datetime.utcnow(), onupdate=db.func.now())
    contract_type = Column(db.String(255))
    expiration_date = Column(db.Date)
    description = Column(db.Text, index=True)
    contract_href = Column(db.Text)
    current_flow = db.relationship('Flow', lazy='subquery')
    flow_id = ReferenceCol('flow', ondelete='SET NULL', nullable=True)
    current_stage = db.relationship('Stage', lazy='subquery')
    current_stage_id = ReferenceCol('stage', ondelete='SET NULL', nullable=True)
    users = db.relationship(
        'User',
        secondary=contract_user_association_table,
        backref='contracts_following',
    )
    starred = db.relationship(
        'User',
        secondary=contract_starred_association_table,
        backref='contracts_starred',
    )
    assigned_to = ReferenceCol('users', ondelete='SET NULL', nullable=True)
    assigned = db.relationship('User', backref=backref(
        'assignments', lazy='dynamic', cascade='none'
    ))

    def __unicode__(self):
        return self.description

class ContractProperty(Model):
    __tablename__ = 'contract_property'

    id = Column(db.Integer, primary_key=True, index=True)
    contract = db.relationship('ContractBase', backref=backref(
        'properties', lazy='dynamic', cascade='all, delete-orphan'
    ))
    contract_id = ReferenceCol('contract', ondelete='CASCADE')
    key = Column(db.String(255), nullable=False)
    value = Column(db.Text)

    def __unicode__(self):
        return '{key}: {value}'.format(key=self.key, value=self.value)

class ContractNote(Model):
    __tablename__ = 'contract_note'

    id = Column(db.Integer, primary_key=True, index=True)
    contract = db.relationship('ContractBase', backref=backref(
        'notes', lazy='dynamic', cascade='all, delete-orphan'
    ))
    contract_id = ReferenceCol('contract', ondelete='CASCADE')
    note = Column(db.Text)
    created_at = Column(db.DateTime, default=datetime.datetime.utcnow())
    updated_at = Column(db.DateTime, default=datetime.datetime.utcnow(), onupdate=db.func.now())

    def __unicode__(self):
        return self.note

class LineItem(Model):
    __tablename__ = 'line_item'

    id = Column(db.Integer, primary_key=True, index=True)
    contract = db.relationship('ContractBase', backref=backref(
        'line_items', lazy='dynamic', cascade='all, delete-orphan'
    ))
    contract_id = ReferenceCol('contract', ondelete='CASCADE')
    description = Column(db.Text, nullable=False, index=True)
    manufacturer = Column(db.Text)
    model_number = Column(db.Text)
    quantity = Column(db.Integer)
    unit_of_measure = Column(db.String(255))
    unit_cost = Column(db.Float)
    total_cost = Column(db.Float)
    percentage = Column(db.Boolean)
    company_name = Column(db.String(255), nullable=True)
    company_id = ReferenceCol('company', nullable=True)

    def __unicode__(self):
        return self.description

# class ContractAudit(Model):
#     __tablename__ = 'contract_audit'

class Stage(Model):
    __tablename__ = 'stage'

    id = Column(db.Integer, primary_key=True, index=True)
    name = Column(db.String(255))

    def __unicode__(self):
        return self.name

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

class ContractStage(Model):
    __tablename__ = 'contract_stage'

    id = Column(
        db.Integer, Sequence('autoincr_contract_stage_id', start=1, increment=1),
        index=True, unique=True
    )
    contract_id = ReferenceCol('contract', ondelete='CASCADE', index=True, primary_key=True)
    contract = db.relationship('ContractBase', backref=backref(
        'stages', lazy='dynamic', cascade='all, delete-orphan'
    ))
    stage_id = ReferenceCol('stage', ondelete='CASCADE', index=True, primary_key=True)
    stage = db.relationship('Stage', backref=backref(
        'contracts', lazy='dynamic', cascade='all, delete-orphan'
    ))
    created_at = Column(db.DateTime, default=datetime.datetime.now())
    # updated_at = Column(db.DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now())
    entered = Column(db.DateTime)
    exited = Column(db.DateTime)
    notes = Column(db.Text)

    def enter(self):
        '''Enter the stage at this point
        '''
        db.session.flush()
        import pdb; pdb.set_trace()
        # ContractBase.query.get(self.contract_id).current_stage_id = self.stage_id
        import pdb; pdb.set_trace()
        self.entered = datetime.datetime.now()

    def exit(self):
        '''Exit the stage
        '''
        self.exited = datetime.datetime.now()

class ContractStageActionItem(Model):
    __tablename__ = 'contract_stage_action_item'

    id = Column(db.Integer, primary_key=True, index=True)
    contract_stage_id = ReferenceCol('contract_stage', ondelete='CASCADE', index=True)
    contract_stage = db.relationship('ContractStage', backref=backref(
        'contract_stage_actions', lazy='dynamic', cascade='all, delete-orphan'
    ))
    action = Column(db.Text)
    taken_at = Column(db.DateTime, default=datetime.datetime.now())

    def __unicode__(self):
        return self.action

class Flow(Model):
    __tablename__ = 'flow'

    id = Column(db.Integer, primary_key=True, index=True)
    flow_name = Column(db.Text, unique=True)
    contract = db.relationship('ContractBase', backref='flow', lazy='subquery')
    stage_order = Column(ARRAY(db.Integer))

    def __unicode__(self):
        return self.flow_name
