# -*- coding: utf-8 -*-

import time
import datetime

from itertools import groupby, ifilter

from sqlalchemy.schema import Table
from sqlalchemy.orm import backref

from purchasing.database import db, Model, Column, RefreshSearchViewMixin, ReferenceCol

from purchasing.filters import days_from_today
from purchasing.data.stages import Stage
from purchasing.data.flows import Flow
from purchasing.data.contract_stages import ContractStage, ContractStageActionItem
from purchasing.users.models import User

contract_user_association_table = Table(
    'contract_user_association', Model.metadata,
    Column('user_id', db.Integer, db.ForeignKey('users.id'), index=True),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id'), index=True),
)

class ContractBase(RefreshSearchViewMixin, Model):
    '''Base contract model

    Attributes:
        id: Primary key unique ID
        financial_id: Financial identifier for the contract.
            In Pittsburgh, this is called the "controller number"
            because it is assigned by the City Controller's office
        expiration_date: Date when the contract expires
        description: Short description of what the contract covers
        contract_href: Link to the actual contract document
        followers: A many-to-many relationship with
            :py:class:`~purchasing.users.models.User` objects
            for people who will receive updates about when the
            contract will be updated
        is_archived: Whether the contract is archived. Archived
            contracts do not appear by default on Scout search

        contract_type_id: Foreign key to
            :py:class:`~purchasing.data.contracts.ContractType`
        contract_type: Sqlalchemy relationship to
            :py:class:`~purchasing.data.contracts.ContractType`
        department_id: Foreign key to
            :py:class:`~purchasing.users.models.Department`
        department: Sqlalchemy relationship to
            :py:class:`~purchasing.users.models.Department`

        opportunity: An :py:class:`~purchasing.opportunities.models.Opportunity`
            created via conductor for this contract

        is_visible: A flag as to whether or not the contract should
            be visible in Conductro
        assigned_to: Foreign key to
            :py:class:`~purchasing.users.models.User`
        assigned: Sqlalchemy relationship to
            :py:class:`~purchasing.users.models.User`
        flow_id: Foreign key to
            :py:class:`~purchasing.data.flows.Flow`
        current_flow: Sqlalchemy relationship to
            :py:class:`~purchasing.data.flows.Flow`
        current_stage_id: Foreign key to
            :py:class:`~purchasing.data.stages.Stage`
        current_stage: Sqlalchemy relationship to
            :py:class:`~purchasing.data.stages.Stage`
        parent_id: Contract self-reference. When new work is started
            on a contract, a clone of that contract is made and
            the contract that was cloned is assigned as the new
            contract's ``parent``
        children: A list of all of this object's children
            (all contracts) that have this contract's id as
            their ``parent_id``
    '''
    __tablename__ = 'contract'

    # base contract information
    id = Column(db.Integer, primary_key=True)
    financial_id = Column(db.String(255))
    expiration_date = Column(db.Date)
    description = Column(db.Text, index=True)
    contract_href = Column(db.Text)
    followers = db.relationship(
        'User',
        secondary=contract_user_association_table,
        backref='contracts_following',
    )
    is_archived = Column(db.Boolean, default=False, nullable=False)

    # contract type/department relationships
    contract_type_id = ReferenceCol('contract_type', ondelete='SET NULL', nullable=True)
    contract_type = db.relationship('ContractType', backref=backref(
        'contracts', lazy='dynamic'
    ))
    department_id = ReferenceCol('department', ondelete='SET NULL', nullable=True, index=True)
    department = db.relationship('Department', backref=backref(
        'contracts', lazy='dynamic', cascade='none'
    ))

    opportunity = db.relationship('Opportunity', uselist=False, backref='opportunity')

    # conductor information
    is_visible = Column(db.Boolean, default=True, nullable=False)
    assigned_to = ReferenceCol('users', ondelete='SET NULL', nullable=True)
    assigned = db.relationship('User', backref=backref(
        'assignments', lazy='dynamic', cascade='none'
    ), foreign_keys=assigned_to)
    flow_id = ReferenceCol('flow', ondelete='SET NULL', nullable=True)
    current_flow = db.relationship('Flow', lazy='joined')
    current_stage_id = ReferenceCol('stage', ondelete='SET NULL', nullable=True, index=True)
    current_stage = db.relationship('Stage', lazy='joined')
    parent_id = Column(db.Integer, db.ForeignKey('contract.id'))
    children = db.relationship('ContractBase', backref=backref(
        'parent', remote_side=[id], lazy='subquery'
    ))

    def __unicode__(self):
        return '{} (ID: {})'.format(self.description, self.id)

    @property
    def scout_contract_status(self):
        '''Returns a string with the contract's status.
        '''
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

    @property
    def current_contract_stage(self):
        '''The contract's current stage

        Because the :py:class:`~purchasing.data.contract_stages.ContractStage` model
        has a three-part compound primary key, we pass the contract's ID, the
        contract's :py:class:`~purchasing.data.flows.Flow` id and its
        :py:class:`~purchasing.data.stages.Stage` id
        '''
        return ContractStage.get_one(self.id, self.flow.id, self.current_stage.id)

    def get_spec_number(self):
        '''Returns the spec number for a given contract

        The spec number is a somewhat unique identifier for contracts used by
        Allegheny County. Because of the history of purchasing between the City
        and the County, the City uses spec numbers when they are available (
        this tends to be contracts with County, A-Bid, and B-Bid
        :py:class:`~purchasing.data.contracts.ContractType`.

        The majority of contracts do not have spec numbers, but these numbers
        are quite important and used regularly for the contracts that do have them.

        Returns:
            A :py:class:`~purchasing.data.contracts.ContractProperty` object, either
            with the key of "Spec Number" or an empty object if none with that name
            exists
        '''
        try:
            return [i for i in self.properties if i.key.lower() == 'spec number'][0]
        except IndexError:
            return ContractProperty()

    def update_with_spec_number(self, data, company=None):
        '''Action to update both a contract and its spec number

        Because a spec number is not a direct property of a contract,
        we have to go through some extra steps to update it.

        Arguments:
            data: Form data to use in updating a contract

        Keyword Arguments:
            company: A :py:class:`~purchasing.data.companies.Company` to
                add to the companies that are servicing the contract
        '''
        spec_number = self.get_spec_number()

        new_spec = data.pop('spec_number', None)
        if new_spec:
            spec_number.key = 'Spec Number'
            spec_number.value = new_spec
        else:
            spec_number.key = 'Spec Number'
            spec_number.value = None
        self.properties.append(spec_number)

        if company and company not in self.companies:
            self.companies.append(company)

        self.update(**data)

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

    def filter_action_log(self):
        '''Returns a filtered action log for this contract

        Because stages can be restarted, simple ordering by time an action was
        taken will lead to incorrectly ordered (and far too many) actions. Filtering
        these down is a multi-step process, which proceeds roughly as follows:

        1. Sort all actions based on the time that they were taken. This ensures
           that when we filter, we will get the most recent action. Putting them
           into proper time order for display takes place later
        2. Group actions by their respective :py:class:`~purchasing.data.stages.Stage`
        3. For each group of actions that takes place in each stage:

            a. Grab the most recent start or restart action for that stage (filtered
               by whether that action was taken on a stage prior to our current stage
               in our flow's stage order)
            b. Grab the most recent end action for that stage (filtered
               by whether that action was taken on a stage prior to our current stage
               in our flow's stage order, or the same stage)
            c. Grab all other actions that took place on that stage
        4. Re-sort them based on the action's sort key, which will put them into the
           proper order for display
        '''
        all_actions = sorted(
            self.build_complete_action_log(), key=lambda x: (
                x.contract_stage.stage_id, -time.mktime(x.taken_at.timetuple())
            )
        )

        filtered_actions = []

        for stage_id, group_of_actions in groupby(all_actions, lambda x: x.contract_stage.stage_id):
            actions = list(group_of_actions)
            # append start types
            filtered_actions.append(next(
                ifilter(
                    lambda x: x.is_start_type and x.contract_stage.happens_before_or_on(self.current_stage_id), actions
                ),
                [])
            )
            # append end types
            filtered_actions.append(next(
                ifilter(
                    lambda x: x.is_exited_type and x.contract_stage.happens_before(self.current_stage_id), actions
                ), [])
            )
            # extend with all other types
            filtered_actions.extend([x for x in actions if x.is_other_type])

        # return the resorted
        return sorted(ifilter(lambda x: hasattr(x, 'taken_at'), filtered_actions), key=lambda x: x.get_sort_key())

    def get_contract_stages(self):
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
            ContractStage.contract_id == self.id,
            ContractStage.flow_id == self.flow_id
        ).order_by(ContractStage.id).all()

    def get_current_stage(self):
        '''Returns the details for the current contract stage
        '''
        return ContractStage.query.filter(
            ContractStage.contract_id == self.id,
            ContractStage.stage_id == self.current_stage_id,
            ContractStage.flow_id == self.flow_id
        ).first()

    def get_first_stage(self):
        '''Get the first ContractStage for this contract

        Returns:
            :py:class:`~purchasing.data.contract_stage.ContractStage` object
            representing the first stage, or None if no stage exists
        '''
        if self.flow:
            return ContractStage.query.filter(
                ContractStage.contract_id == self.id,
                ContractStage.stage_id == self.flow.stage_order[0],
                ContractStage.flow_id == self.flow_id
            ).first()
        return None

    def completed_last_stage(self):
        '''Boolean to check if we have completed the last stage of our flow
        '''
        return self.flow is None or \
            self.current_stage_id == self.flow.stage_order[-1] and \
            self.get_current_stage().exited is not None

    def add_follower(self, user):
        '''Add a follower from a contract's list of followers

        Arguments:
            user: A :py:class:`~purchasing.users.models.User`

        Returns:
            A two-tuple to use to flash an alert of (the message to display,
            the class to style the message with)
        '''
        if user not in self.followers:
            self.followers.append(user)
            return ('Successfully subscribed!', 'alert-success')
        return ('Already subscribed!', 'alert-info')

    def remove_follower(self, user):
        '''Remove a follower from a contract's list of followers

        Arguments:
            user: A :py:class:`~purchasing.users.models.User`

        Returns:
            A two-tuple to use to flash an alert of (the message to display,
            the class to style the message with)
        '''
        if user in self.followers:
            self.followers.remove(user)
            return ('Successfully unsubscribed', 'alert-success')
        return ('You haven\'t subscribed to this contract!', 'alert-warning')

    def transfer_followers_to_children(self):
        '''Transfer relationships from parent to all children and reset parent's followers
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

    def complete(self):
        '''Do the steps to mark a contract as complete

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

    def kill(self):
        '''Remove the contract from the conductor visiblility list
        '''
        self.is_visible = False
        self.is_archived = True
        if not self.description.endswith(' [Archived]'):
            self.description += ' [Archived]'

    @classmethod
    def clone(cls, instance, parent_id=None, strip=True, new_conductor_contract=True):
        '''Takes a contract object and clones it

        The clone always strips the following properties:

        * Current Stage

        If the strip flag is set to true, the following are also stripped

        * Contract HREF
        * Financial ID
        * Expiration Date

        If the new_conductor_contract flag is set to true, the following are set:

        * is_visible set to False
        * is_archived set to False

        Relationships are handled as follows:

        * Stage, Flow - Duplicated
        * Properties, Notes, Line Items, Companies, Stars, Follows kept on old

        Arguments:
            instance: The instance of the contract to clone, will become
                the parent of the cloned contract unless a different
                ``parent_id`` is passed as a keyword argument

        Keyword Arguments:
            parent_id: The parent id of the contract to be passed, defaults to None
            strip: Boolean, if true, the contract href, financial id and expiration
                date of the cloned contract will all be stripped. Defaults to True
            new_conductor_contract: Boolean to mark if we are going to be starting
                new work in Conductor with the clone. If true, set both
                ``is_visible`` and ``is_archived`` to False. Defaults to True

        Returns:
            The cloned contract created from the passed instance
        '''
        clone = cls(**instance.as_dict())
        clone.id, clone.current_stage = None, None

        clone.parent_id = parent_id if parent_id else instance.id

        if strip:
            clone.contract_href, clone.financial_id, clone.expiration_date = None, None, None

        if new_conductor_contract:
            clone.is_archived, clone.is_visible = False, False

        return clone

    def _transition_to_first(self, user, complete_time):
        contract_stage = ContractStage.get_one(
            self.id, self.flow.id, self.flow.stage_order[0]
        )

        self.current_stage_id = self.flow.stage_order[0]
        return [contract_stage.log_enter(user, complete_time)]

    def _transition_to_next(self, user, complete_time):
        stages = self.flow.stage_order
        current_stage_idx = stages.index(self.current_stage.id)

        current_stage = self.current_contract_stage
        next_stage = ContractStage.get_one(
            self.id, self.flow.id, self.flow.stage_order[current_stage_idx + 1]
        )

        self.current_stage_id = next_stage.stage.id
        return [current_stage.log_exit(user, complete_time), next_stage.log_enter(user, complete_time)]

    def _transition_to_last(self, user, complete_time):
        exit = self.current_contract_stage.log_exit(user, complete_time)
        return [exit]

    def _transition_backwards_to_destination(self, user, destination, complete_time):
        destination_idx = self.flow.stage_order.index(destination)
        current_stage_idx = self.flow.stage_order.index(self.current_stage_id)

        if destination_idx > current_stage_idx:
            raise Exception('Skipping stages is not currently supported')

        stages = self.flow.stage_order[destination_idx:current_stage_idx + 1]
        to_revert = ContractStage.get_multiple(self.id, self.flow_id, stages)

        actions = []
        for contract_stage_ix, contract_stage in enumerate(to_revert):
            if contract_stage_ix == 0:
                actions.append(contract_stage.log_reopen(user, complete_time))
                contract_stage.entered = complete_time
                contract_stage.exited = None
                self.current_stage_id = contract_stage.stage.id
            else:
                contract_stage.full_revert()

        return actions

    def transition(self, user, destination=None, complete_time=None):
        '''Transition the contract to the appropriate stage.

        * If the contract has no current stage, transition it to the first
          stage
        * If the contract has a "destination", transition it to that destination
        * If the current stage of the contract is the last stage of the contract's
          flow order, exit the last stage and move to completion
        * If it is anything else, transition forward one stage in the flow order

        Arguments:
            user: The user taking the actions

        Keyword Arguments:
            destination: An optional revere destination to allow for rewinding
                to any point in time. Defaults to None
            complete_time: A time other than the current time to perform
                the transitions. If one is given, the relevant
                :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
                datetime fields
                and :py:class:`~purchasing.data.contract_stages.ContractStage`
                enter and exit times are marked with the passed time. The actions'
                taken_at times are still marked with the current time, however.

        Returns:
            A list of :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
            objects which describe the actions in transition
        '''
        complete_time = complete_time if complete_time else datetime.datetime.utcnow()
        if self.current_stage_id is None:
            actions = self._transition_to_first(user, complete_time)
        elif destination is not None:
            actions = self._transition_backwards_to_destination(user, destination, complete_time)
        elif self.current_stage_id == self.flow.stage_order[-1]:
            actions = self._transition_to_last(user, complete_time)
        else:
            actions = self._transition_to_next(user, complete_time)

        return actions

    def switch_flow(self, new_flow_id, user):
        '''Switch the contract's progress from one flow to another

        Instead of trying to do anything too smart, we prefer instead
        to be dumb -- it is better to force the user to click ahead
        through a bunch of stages than it is to incorrectly fast-forward
        them to an incorrect state.

        There are five concrete actions here:

        1. Fully revert all stages in the old flow
        2. Rebuild our flow/stage model for the new order.
        3. Attach the complete log of the old flow into the first stage
           of the new order.
        4. Strip the contract's current stage id.
        5. Transition into the first stage of the new order. This will
           ensure that everything is being logged in the correct order.

        Arguments:
            new_flow_id: ID of the new flow to switch to
            user: The user performing the switch
        '''
        old_flow = self.flow.flow_name
        old_action_log = self.filter_action_log()

        new_flow = Flow.query.get(new_flow_id)

        # fully revert all used stages in the old flow
        for contract_stage in ContractStage.query.filter(
            ContractStage.contract_id == self.id,
            ContractStage.flow_id == self.flow_id,
            ContractStage.entered != None
        ).all():
            contract_stage.full_revert()
            contract_stage.strip_actions()

        db.session.commit()

        # create the new stages
        new_stages, new_contract_stages, revert = new_flow.create_contract_stages(self)

        # log that we are switching flows into the first stage
        switch_log = ContractStageActionItem(
            contract_stage_id=new_contract_stages[0].id, action_type='flow_switch',
            taken_by=user.id, taken_at=datetime.datetime.utcnow(),
            action_detail={
                'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
                'date': datetime.datetime.utcnow().strftime('%Y-%m-%d'),
                'type': 'flow_switched', 'old_flow': old_flow,
                'new_flow': self.flow.flow_name,
                'old_flow_actions': [i.as_dict() for i in old_action_log]
            }
        )
        db.session.add(switch_log)
        db.session.commit()

        # remove the current_stage_id from the contract
        # so we can start the new flow
        self.current_stage_id = None
        self.flow_id = new_flow_id

        destination = None
        if revert:
            destination = new_stages[0]

        # transition into the first stage of the new flow
        actions = self.transition(user, destination=destination)
        for i in actions:
            db.session.add(i)

        db.session.commit()
        return new_contract_stages[0], self

    def build_subscribers(self):
        '''Build a list of subscribers and others to populate contacts in conductor
        '''
        department_users, county_purchasers, eorc = User.get_subscriber_groups(self.department_id)

        if self.parent is None:
            followers = []
        else:
            followers = [i for i in self.parent.followers if i not in department_users]

        subscribers = {
            'Department Users': department_users,
            'Followers': followers,
            'County Purchasers': [i for i in county_purchasers if i not in department_users],
            'EORC': eorc
        }
        return subscribers, sum([len(i) for i in subscribers.values()])

class ContractType(Model):
    '''Model for contract types

    Attributes:
        id: Primary key unique ID
        name: Name of the contract type
        allow_opportunities: Boolean flag as to whether to allow
            opportunities to be posted
        opportunity_response_instructions: HTML string of instructions
            for bidders on how to respond to opportunities of this
            type
    '''
    __tablename__ = 'contract_type'

    id = Column(db.Integer, primary_key=True, index=True)
    name = Column(db.String(255))
    allow_opportunities = Column(db.Boolean, default=False)
    opportunity_response_instructions = Column(db.Text)

    def __unicode__(self):
        return self.name if self.name else ''

    @classmethod
    def opportunity_type_query(cls):
        '''Query factory filtered to include only types that allow opportunities
        '''
        return cls.query.filter(cls.allow_opportunities == True)

    @classmethod
    def query_factory_all(cls):
        '''Query factory to return all contract types
        '''
        return cls.query.order_by(cls.name)

    @classmethod
    def get_type(cls, type_name):
        '''Get an individual type based on a passed type name

        Arguments:
            type_name: Name of the type to look up

        Returns:
            One :py:class:`~purchasing.data.contracts.ContractType` object
        '''
        return cls.query.filter(db.func.lower(cls.name) == type_name.lower()).first()

class ContractProperty(RefreshSearchViewMixin, Model):
    '''Model for contract properties

    The contract property model effectively serves as a key-value
    storage unit for properties that exist on a subset of contracts.
    For example, a common unit for County contracts is the so-called
    "spec number", an identified used by Allegheny County for their
    electronic bidding system. Other contract types (such as PA state and
    COSTARS contracts), do not have this property but do have others
    (such as manufacturers offered, etc.). Therefore, we use this
    model as an extended key-value store for the base
    :py:class:`~purchasing.data.contracts.ContractBase` model

    Attributes:
        id: Primary key unique ID
        contract: Sqlalchemy relationship to
            :py:class:`~purchasing.data.contracts.ContractBase`
        contract_id: Foreign key to
            :py:class:`~purchasing.data.contracts.ContractBase`
        key: The key for the property (for example, Spec Number)
        value: The value for the property (for example, 7137)
    '''
    __tablename__ = 'contract_property'

    id = Column(db.Integer, primary_key=True, index=True)
    contract = db.relationship('ContractBase', backref=backref(
        'properties', lazy='joined', cascade='all, delete-orphan'
    ))
    contract_id = ReferenceCol('contract', ondelete='CASCADE')
    key = Column(db.String(255), nullable=False)
    value = Column(db.Text)

    def __unicode__(self):
        return '{key}: {value}'.format(key=self.key, value=self.value)

class ContractNote(Model):
    '''Model for contract notes

    Attributes:
        id: Primary key unique ID
        contract: Sqlalchemy relationship to
            :py:class:`~purchasing.data.contracts.ContractBase`
        contract_id: Foreign key to
            :py:class:`~purchasing.data.contracts.ContractBase`
        note: Text of the note to be taken
        taken_by_id: Foreign key to
            :py:class:`~purchasing.users.models.User`
        taken_by: Sqlalchemy relationship to
            :py:class:`~purchasing.users.models.User`
    '''
    __tablename__ = 'contract_note'

    id = Column(db.Integer, primary_key=True, index=True)
    contract = db.relationship('ContractBase', backref=backref(
        'notes', lazy='dynamic', cascade='all, delete-orphan'
    ))
    contract_id = ReferenceCol('contract', ondelete='CASCADE')
    note = Column(db.Text)
    taken_by_id = ReferenceCol('users', ondelete='SET NULL', nullable=True)
    taken_by = db.relationship('User', backref=backref(
        'contract_note', lazy='dynamic', cascade=None
    ), foreign_keys=taken_by_id)

    def __unicode__(self):
        return self.note

class LineItem(RefreshSearchViewMixin, Model):
    '''Model for contract line items

    Attributes:
        id: Primary key unique ID
        contract: Sqlalchemy relationship to
            :py:class:`~purchasing.data.contracts.ContractBase`
        contract_id: Foreign key to
            :py:class:`~purchasing.data.contracts.ContractBase`
        description: Description of the line item in question
        manufacturer: Name of the manufacturer of the line item
        model_number: A model number for the item
        quantity: The quantity of the item on contract
        unit_of_measure: The unit of measure (for example EACH)
        unit_cost: Cost on a per-unit basis
        total_cost: Total cost (unit_cost * quantity)
        percentage: Whether or not the unit cost should be represented
            as a percentage (NOTE: on the BidNet system, there is no
            differentiation between a percentage discount off of an item
            and actual unit cost for an item)
        company_name: Name of the company that is providing the good
        company_id: Foreign key to
            :py:class:`~purchasing.data.companies.Company`
    '''
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
