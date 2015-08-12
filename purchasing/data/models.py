# -*- coding: utf-8 -*-

import datetime
from purchasing.database import (
    Column,
    Model,
    db,
    ReferenceCol
)
from sqlalchemy.dialects.postgres import ARRAY
from sqlalchemy.dialects.postgresql import TSVECTOR, JSON
from sqlalchemy.schema import Table, Sequence
from sqlalchemy.orm import backref

TRIGGER_TUPLES = [
    ('contract', 'description', 'WHEN (NEW.is_visible != False)'),
    ('company', 'company_name', ''),
    ('contract_property', 'value', ''),
    ('line_item', 'description', ''),
]

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
    Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), index=True),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id', ondelete='SET NULL'), index=True),
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
        return '{first} {last}'.format(
            first=self.first_name, last=self.last_name
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
    followers = db.relationship(
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

    department_id = ReferenceCol('department', ondelete='SET NULL', nullable=True)
    department = db.relationship('Department', backref=backref(
        'contracts', lazy='dynamic', cascade='none'
    ))

    is_visible = Column(db.Boolean, default=False, nullable=False)
    is_archived = Column(db.Boolean, default=False, nullable=False)

    opportunity = db.relationship('Opportunity', uselist=False, backref='opportunity')

    parent_id = Column(db.Integer, db.ForeignKey('contract.id'))
    child = db.relationship('ContractBase', backref=backref(
        'parent', remote_side=[id]
    ))

    def __unicode__(self):
        return self.description

    def get_spec_number(self):
        '''Returns the spec number for a given contract
        '''
        try:
            return [i for i in self.properties if i.key.lower() == 'spec number'][0]
        except IndexError:
            return ContractProperty()

    def build_complete_action_log(self):
        '''Returns the complete action log for this contract
        '''
        return ContractStageActionItem.query.join(ContractStage).filter(
            ContractStage.contract_id == self.id
        ).order_by(db.text('taken_at asc')).all()

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
    taken_by_id = ReferenceCol('users', ondelete='SET NULL', nullable=True)
    taken_by = db.relationship('User', backref=backref(
        'contract_note', lazy='dynamic', cascade=None
    ))

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
    post_opportunities = Column(db.Boolean, default=False, nullable=False)

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
    __table_args__ = (db.Index('ix_contrage_stage_combined_id', 'contract_id', 'stage_id', 'flow_id'), )

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

    flow_id = ReferenceCol('flow', ondelete='CASCADE', index=True, primary_key=True)
    flow = db.relationship('Flow', backref=backref(
        'contract_stages', lazy='dynamic', cascade='all, delete-orphan'
    ))

    created_at = Column(db.DateTime, default=datetime.datetime.now())
    updated_at = Column(db.DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now())
    entered = Column(db.DateTime)
    exited = Column(db.DateTime)
    notes = Column(db.Text)

    def enter(self):
        '''Enter the stage at this point
        '''
        self.entered = datetime.datetime.now()

    def exit(self):
        '''Exit the stage
        '''
        self.exited = datetime.datetime.now()

    def full_revert(self):
        '''Clear timestamps for both enter and exit
        '''
        self.entered = None
        self.exited = None

    def strip_actions(self):
        '''Clear out non-stage-switch actions

        This will prevent duplicate actions from piling up
        in the stream that is presented to the user
        '''
        for action in self.contract_stage_actions:
            if action.action_type != 'flow_switch':
                action.delete()
        return None

    @property
    def is_current_stage(self):
        '''Checks to see if this is the current stage
        '''
        return True if self.entered and not self.exited else False

class ContractStageActionItem(Model):
    __tablename__ = 'contract_stage_action_item'

    id = Column(db.Integer, primary_key=True, index=True)
    contract_stage_id = ReferenceCol('contract_stage', ondelete='CASCADE', index=True)
    contract_stage = db.relationship('ContractStage', backref=backref(
        'contract_stage_actions', lazy='dynamic', cascade='all, delete-orphan'
    ))
    action_type = Column(db.String(255))
    action_detail = Column(JSON)
    taken_at = Column(db.DateTime, default=datetime.datetime.now())
    taken_by = ReferenceCol('users', ondelete='SET NULL', nullable=True)
    taken_by_user = db.relationship('User', backref=backref(
        'contract_stage_actions', lazy='dynamic'
    ))

    def __unicode__(self):
        return self.action

    def get_sort_key(self):
        # if we are reversion, we need to get the timestamps from there
        if self.action_type == 'reversion':
            return datetime.datetime.strptime(
                self.action_detail['timestamp'],
                '%Y-%m-%dT%H:%M:%S'
            )
        # otherwise, return the taken_at time
        else:
            return self.taken_at if self.taken_at else datetime.datetime(1970, 1, 1)

    @property
    def non_null_items(self):
        return dict((k, v) for (k, v) in self.action_detail.items() if v is not None)

    @property
    def non_null_items_count(self):
        return len(self.non_null_items)

class Flow(Model):
    __tablename__ = 'flow'

    id = Column(db.Integer, primary_key=True, index=True)
    flow_name = Column(db.Text, unique=True)
    contract = db.relationship('ContractBase', backref='flow', lazy='subquery')
    stage_order = Column(ARRAY(db.Integer))

    def __unicode__(self):
        return self.flow_name
