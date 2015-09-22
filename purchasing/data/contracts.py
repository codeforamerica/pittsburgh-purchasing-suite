# -*- coding: utf-8 -*-

import datetime

from sqlalchemy.schema import Table
from sqlalchemy.orm import backref

from purchasing.database import db, Model, Column, RefreshSearchViewMixin, ReferenceCol

from purchasing.filters import days_from_today
from purchasing.data.contract_stages import ContractStage, ContractStageActionItem

contract_user_association_table = Table(
    'contract_user_association', Model.metadata,
    Column('user_id', db.Integer, db.ForeignKey('users.id'), index=True),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id'), index=True),
)

class ContractBase(RefreshSearchViewMixin, Model):
    __tablename__ = 'contract'

    id = Column(db.Integer, primary_key=True)
    financial_id = Column(db.String(255))
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

    contract_type_id = ReferenceCol('contract_type', ondelete='SET NULL', nullable=True)
    contract_type = db.relationship('ContractType', backref=backref(
        'contracts', lazy='dynamic'
    ))

    assigned_to = ReferenceCol('users', ondelete='SET NULL', nullable=True)
    assigned = db.relationship('User', backref=backref(
        'assignments', lazy='dynamic', cascade='none'
    ), foreign_keys=assigned_to)

    department_id = ReferenceCol('department', ondelete='SET NULL', nullable=True)
    department = db.relationship('Department', backref=backref(
        'contracts', lazy='dynamic', cascade='none'
    ))

    is_visible = Column(db.Boolean, default=True, nullable=False)
    is_archived = Column(db.Boolean, default=False, nullable=False)

    opportunity = db.relationship('Opportunity', uselist=False, backref='opportunity')

    parent_id = Column(db.Integer, db.ForeignKey('contract.id'))
    children = db.relationship('ContractBase', backref=backref(
        'parent', remote_side=[id]
    ))

    def __unicode__(self):
        return self.description

    @property
    def scout_contract_status(self):
        if self.expiration_date:
            if days_from_today(self.expiration_date) <= 0 and self.children and self.is_archived:
                return 'expired_replaced'
            elif days_from_today(self.expiration_date) <= 0:
                return 'expired'
            elif self.children and self.is_archived:
                return 'replaced'
            elif self.is_archived:
                return 'archived'
        elif self.children and self.is_archived:
            return 'replaced'
        elif self.is_archived:
            return 'archived'
        return 'active'

    def get_spec_number(self):
        '''Returns the spec number for a given contract
        '''
        try:
            return [i for i in self.properties if i.key.lower() == 'spec number'][0]
        except IndexError:
            return ContractProperty()

    def update_with_spec_number(self, data, company=None):
        spec_number = self.get_spec_number()

        new_spec = data.pop('spec_number', None)
        if new_spec:
            spec_number.key = 'Spec Number'
            spec_number.value = new_spec
        else:
            spec_number.key = 'Spec Number'
            spec_number.value = None
        self.properties.append(spec_number)

        if company:
            self.companies.append(company)

        self.update(**data)

        return spec_number

    def build_complete_action_log(self):
        '''Returns the complete action log for this contract
        '''
        return ContractStageActionItem.query.join(ContractStage).filter(
            ContractStage.contract_id == self.id
        ).order_by(
            ContractStageActionItem.taken_at,
            ContractStage.id,
            ContractStageActionItem.id
        ).all()

    def get_current_stage(self):
        '''Returns the details for the current contract stage
        '''
        return ContractStage.query.filter(
            ContractStage.contract_id == self.id,
            ContractStage.stage_id == self.current_stage_id,
            ContractStage.flow_id == self.flow_id
        ).first()

    def completed_last_stage(self):
        '''Boolean to check if we have completed the last stage of our flow
        '''
        return self.flow is None or \
            self.current_stage_id == self.flow.stage_order[-1] and \
            self.get_current_stage().exited is not None

    def add_follower(self, user):
        if user not in self.followers:
            self.followers.append(user)
            return ('Successfully subscribed!', 'alert-success')
        return ('Already subscribed!', 'alert-info')

    def remove_follower(self, user):
        if user in self.followers:
            self.followers.remove(user)
            return ('Successfully unsubscribed', 'alert-success')
        return ('You haven\'t subscribed to this contract!', 'alert-warning')

    def transfer_followers_to_children(self):
        '''Transfer relationships from parent to all children
        '''
        for child in self.children:
            child.followers = self.followers

        self.followers = []
        return self.followers

    def extend(self, delete_children=True):
        '''Extends a contract.

        Because conductor clones existing contracts when work begins,
        when we get an "extend" signal, we actually want to extend the
        parent conract of the clone. Optionally (by default), we also
        want to delete the child (cloned) contract.
        '''
        self.expiration_date = None

        if delete_children:
            for child in self.children:
                child.delete()
            self.children = []

        return self

    def complete(self):
        '''Do the steps to mark a contract as complete:

        1. Transfer the followers to children
        2. Modify description to make contract explicitly completed/archived
        3. Mark self as archived and not visible
        4. Mark children as not archived and visible
        '''
        self.transfer_followers_to_children()
        self.kill()

        for child in self.children:
            child.is_archived = False
            child.is_visible = True

        return self

    def kill(self):
        '''Remove the contract from the conductor visiblility list
        '''
        self.is_visible = False
        self.is_archived = True
        if not self.description.endswith(' [Archived]'):
            self.description += ' [Archived]'
        return self

    @classmethod
    def clone(cls, instance, parent_id=None, strip=True, new_conductor_contract=True):
        '''Takes a contract object and clones it

        The clone always strips the following properties:
            + Assigned To
            + Current Stage

        If the strip flag is set to true, the following are also stripped
            + Contract HREF
            + Financial ID
            + Expiration Date

        If the new_conductor_contract flag is set to true, the following are set:
            + is_visible set to False
            + is_archived set to False

        Relationships are handled as follows:
            + Stage, Flow - Duplicated
            + Properties, Notes, Line Items, Companies, Stars, Follows kept on old
        '''
        clone = cls(**instance.as_dict())
        clone.id, clone.assigned_to, clone.current_stage = None, None, None

        clone.parent_id = parent_id if parent_id else instance.id

        if strip:
            clone.contract_href, clone.financial_id, clone.expiration_date = None, None, None

        if new_conductor_contract:
            clone.is_archived, clone.is_visible = False, False

        return clone

    def _transition_to_first(self, user):
        contract_stage = ContractStage.get_one(
            self.id, self.flow.id, self.flow.stage_order[0]
        )

        self.current_stage_id = self.flow.stage_order[0]
        return [contract_stage.log_enter(user)]

    def _transition_to_next(self, user):
        stages = self.flow.stage_order
        current_stage_idx = stages.index(self.current_stage.id)

        current_stage = ContractStage.get_one(self.id, self.flow.id, self.current_stage.id)

        next_stage = ContractStage.get_one(
            self.id, self.flow.id, self.flow.stage_order[current_stage_idx + 1]
        )

        self.current_stage_id = next_stage.stage.id
        return [current_stage.log_exit(user), next_stage.log_enter(user)]

    def _transition_to_last(self, user):
        current_stage = ContractStage.get_one(self.id, self.flow.id, self.current_stage.id)
        exit = current_stage.log_exit(user)
        self.parent.complete()
        return [exit]

    def _transition_backwards_to_destination(self, user, destination):
        destination_idx = self.flow.stage_order.index(destination)
        current_stage_idx = self.flow.stage_order.index(self.current_stage_id)

        if destination_idx > current_stage_idx:
            raise Exception('Skipping stages is not currently supported')

        stages = self.flow.stage_order[destination_idx:current_stage_idx + 1]
        to_revert = ContractStage.get_multiple(self.id, self.flow_id, stages)

        actions = []
        for contract_stage_ix, contract_stage in enumerate(to_revert):
            if contract_stage_ix == 0:
                actions.append(contract_stage.log_reopen(user))
                contract_stage.entered = datetime.datetime.now()
                contract_stage.exited = None
                self.current_stage_id = contract_stage.stage.id
            else:
                contract_stage.full_revert()

        return actions

    def transition(self, user, destination=None, *args, **kwargs):
        '''Routing method -- figure out which actual method to call
        '''
        if self.current_stage_id is None:
            actions = self._transition_to_first(user)
        elif destination is not None:
            actions = self._transition_backwards_to_destination(user, destination)
        elif self.current_stage_id == self.flow.stage_order[-1]:
            actions = self._transition_to_last(user)
        else:
            actions = self._transition_to_next(user)

        return actions

class ContractType(Model):
    __tablename__ = 'contract_type'

    id = Column(db.Integer, primary_key=True, index=True)
    name = Column(db.String(255))
    allow_opportunities = Column(db.Boolean, default=False)
    opportunity_response_instructions = Column(db.Text)

    def __unicode__(self):
        return self.name if self.name else ''

    @classmethod
    def opportunity_type_query(cls):
        return cls.query.filter(cls.allow_opportunities == True)

    @classmethod
    def query_factory_all(cls):
        return cls.query.order_by(cls.name)

class ContractProperty(RefreshSearchViewMixin, Model):
    __tablename__ = 'contract_property'

    id = Column(db.Integer, primary_key=True, index=True)
    contract = db.relationship('ContractBase', backref=backref(
        'properties', lazy='subquery', cascade='all, delete-orphan'
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
    ), foreign_keys=taken_by_id)

    def __unicode__(self):
        return self.note

class LineItem(RefreshSearchViewMixin, Model):
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
