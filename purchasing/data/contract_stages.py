# -*- coding: utf-8 -*-

import datetime

from sqlalchemy.schema import Sequence
from sqlalchemy.orm import backref
from sqlalchemy.dialects.postgresql import JSON

from purchasing.database import Model, db, Column, ReferenceCol

class ContractStage(Model):
    '''Model for contract stages

    A Contract Stage is the term for a step that a
    :py:class:`~purchasing.data.contracts.ContractBase` will
    occupy while going through a
    :py:class:`~purchasing.data.flows.Flow`. It has a
    three-part compound primary key of ``contract_id``,
    ``stage_id``, and ``flow_id``. A contract stage's primary role
    is to keep track of how long things take, which is accomplished
    through the object's ``enter`` and ``exit`` attributes.

    Attributes:
        id: Unique ID for each contract/stage/flow contract stage
        contract_id: Part of compound primary key, foreign key to
            :py:class:`~purchasing.data.contracts.ContractBase`
        contract: Sqlalchemy relationship to
            :py:class:`~purchasing.data.contracts.ContractBase`
        stage_id: Part of compound primary key, foreign key to
            :py:class:`~purchasing.data.stages.Stage`
        stage: Sqlalchemy relationship to
            :py:class:`~purchasing.data.stages.Stage`
        flow_id: Part of compound primary key, foreign key to
            :py:class:`~purchasing.data.flows.Flow`
        flow: Sqlalchemy relationship to
            :py:class:`~purchasing.data.flows.Flow`
        entered: When work started for this particular contract stage
        exited: When work completed for this particular contract stage
    '''

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

    entered = Column(db.DateTime)
    exited = Column(db.DateTime)

    @property
    def is_current_stage(self):
        '''Checks to see if this is the current stage
        '''
        return True if self.entered and not self.exited else False

    @classmethod
    def get_one(cls, contract_id, flow_id, stage_id):
        '''Get one contract stage based on its three primary key elements

        Arguments:
            contract_id: ID of the relevant
                :py:class:`~purchasing.data.contracts.ContractBase`
            flow_id: ID of the relevant
                :py:class:`~purchasing.data.flows.Flow`
            stage_id: ID of the relevant
                :py:class:`~purchasing.data.stages.Stage`
        '''
        return cls.query.filter(
            cls.contract_id == contract_id,
            cls.stage_id == stage_id,
            cls.flow_id == flow_id
        ).first()

    @classmethod
    def get_multiple(cls, contract_id, flow_id, stage_ids):
        '''Get multiple contract stages based on multiple flow ids

        Multiple only takes a single contract id and flow id because
        in Conductor, you would have multiple
        :py:class:`~purchasing.data.stages.Stage` per
        :py:class:`~purchasing.data.contracts.ContractBase`/
        :py:class:`~purchasing.data.flows.Flow` combination.

        Arguments:
            contract_id: ID of the relevant
                :py:class:`~purchasing.data.contracts.ContractBase`
            flow_id: ID of the relevant
                :py:class:`~purchasing.data.flows.Flow`
            stage_id: IDs of the relevant
                :py:class:`~purchasing.data.stages.Stage`
        '''
        return cls.query.filter(
            cls.contract_id == contract_id,
            cls.stage_id.in_(stage_ids),
            cls.flow_id == flow_id
        ).order_by(cls.id).all()

    def enter(self, enter_time=None):
        '''Set the contract stage's enter time

        Arguments:
            enter_time: A datetime for this stage's enter attribute.
                Defaults to utcnow.
        '''
        enter_time = enter_time if enter_time else datetime.datetime.utcnow()
        self.entered = enter_time

    def log_enter(self, user, enter_time):
        '''Enter the contract stage and log its entry

        Arguments:
            user: A :py:class:`~purchasing.users.models.User` object
                who triggered the enter event.
            enter_time: A datetime for this stage's enter attribute.

        Returns:
            A :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
            that represents the log of the action item.
        '''
        self.enter(enter_time=enter_time)
        return ContractStageActionItem(
            contract_stage_id=self.id, action_type='entered',
            taken_by=user.id, taken_at=datetime.datetime.utcnow(),
            action_detail={
                'timestamp': self.entered.strftime('%Y-%m-%dT%H:%M:%S'),
                'date': self.entered.strftime('%Y-%m-%d'),
                'type': 'entered', 'label': 'Started work',
                'stage_name': self.stage.name
            }
        )

    def happens_before(self, target_stage_id):
        '''Check if this contract stage happens before a target stage

        "Before" refers to the relative positions of these stages
        in their linked flow's stage order based on the contract stage's
        ``stage_id``. If the passed ``target_stage_id``
        is not in the flow's stage order, this always returns False.

        Arguments:
            target_stage_id: A :py:class:`purchasing.data.stages.Stage` ID
        '''
        if target_stage_id not in self.flow.stage_order:
            return False
        return self.flow.stage_order.index(self.stage_id) < \
            self.flow.stage_order.index(target_stage_id)

    def happens_before_or_on(self, target_stage_id):
        '''Check if this contract stage happens before or is a target stage

        "Before" refers to the relative positions of these stages
        in their linked flow's stage order based on the contract stage's
        ``stage_id``. "On" refers to whether or not
        the passed ``target_stage_id`` shares an index with the contract
        stage's ``stage_id``. If the passed ``target_stage_id``
        is not in the flow's stage order, this always returns False.

        Arguments:
            target_stage_id: A :py:class:`purchasing.data.stages.Stage` ID
        '''
        if target_stage_id not in self.flow.stage_order:
            return False
        return self.flow.stage_order.index(self.stage_id) <= \
            self.flow.stage_order.index(target_stage_id)

    def happens_after(self, target_stage_id):
        '''Check if this contract stage happens after a target stage

        "after" refers to the relative positions of these stages
        in their linked flow's stage order based on the contract stage's
        ``stage_id``. If the passed ``target_stage_id``
        is not in the flow's stage order, this always returns False.

        Arguments:
            target_stage_id: A :py:class:`purchasing.data.stages.Stage` ID
        '''
        if target_stage_id not in self.flow.stage_order:
            return False
        return self.flow.stage_order.index(self.stage_id) > \
            self.flow.stage_order.index(target_stage_id)

    def exit(self, exit_time=None):
        '''Set the contract stage's exit time

        Arguments:
            exit_time: A datetime for this stage's exit attribute.
                Defaults to utcnow.
        '''
        exit_time = exit_time if exit_time else datetime.datetime.utcnow()
        self.exited = exit_time

    def log_exit(self, user, exit_time):
        '''Exit the contract stage and log its exit

        Arguments:
            user: A :py:class:`~purchasing.users.models.User` object
                who triggered the exit event.
            exit_time: A datetime for this stage's exit attribute.

        Returns:
            A :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
            that represents the log of the action item.
        '''
        self.exit(exit_time=exit_time)
        return ContractStageActionItem(
            contract_stage_id=self.id, action_type='exited',
            taken_by=user.id, taken_at=datetime.datetime.utcnow(),
            action_detail={
                'timestamp': self.exited.strftime('%Y-%m-%dT%H:%M:%S'),
                'date': self.exited.strftime('%Y-%m-%d'),
                'type': 'exited', 'label': 'Completed work',
                'stage_name': self.stage.name
            }
        )

    def log_reopen(self, user, reopen_time):
        '''Reopen the contract stage and log that re-opening

        Arguments:
            user: A :py:class:`~purchasing.users.models.User` object
                who triggered the reopen event.
            reopen_time: A datetime for this stage's reopen attribute.

        Returns:
            A :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
            that represents the log of the action item.
        '''
        return ContractStageActionItem(
            contract_stage_id=self.id, action_type='reversion',
            taken_by=user.id, taken_at=datetime.datetime.utcnow(),
            action_detail={
                'timestamp': reopen_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'date': datetime.datetime.utcnow().strftime('%Y-%m-%d'),
                'type': 'reopened', 'label': 'Restarted work',
                'stage_name': self.stage.name,
            }
        )

    def log_extension(self, user):
        '''Log an extension event

        Arguments:
            user: A :py:class:`~purchasing.users.models.User` object
                who triggered the extension event.

        Returns:
            A :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
            that represents the log of the action item.
        '''
        return ContractStageActionItem(
            contract_stage_id=self.id, action_type='extension',
            taken_by=user.id, taken_at=datetime.datetime.utcnow(),
            action_detail={
                'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
                'date': datetime.datetime.utcnow().strftime('%Y-%m-%d'),
                'type': 'extension', 'stage_name': self.stage.name
            }
        )

    def full_revert(self):
        '''Clear timestamps for both enter and exit for this contract stage
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

    def __unicode__(self):
        return '{} - {}'.format(self.contract.description, self.stage.name)

class ContractStageActionItem(Model):
    '''Action logs for various actions that take place on a contract stage

    Attributes:
        id: Primary key unique ID
        contract_stage_id: Foreign key to
            :py:class:`~purchasing.data.contract_stages.ContractStage`
        contract_stage: Sqlalchemy relationship to
            :py:class:`~purchasing.data.contract_stages.ContractStage`
        action_type: A string describing the type of action taken
        action_detail: A JSON blob representing details pertinent
            to the action in question
        taken_at: Timestamp for when the action was taken
        taken_by: Foriegn key to
            :py:class:`~purchasing.users.models.User`
        taken_by_user: Sqlalchemy relationship to
            :py:class:`~purchasing.users.models.User`
    '''
    __tablename__ = 'contract_stage_action_item'

    id = Column(db.Integer, primary_key=True, index=True)
    contract_stage_id = ReferenceCol('contract_stage', ondelete='CASCADE', index=True)
    contract_stage = db.relationship('ContractStage', backref=backref(
        'contract_stage_actions', lazy='dynamic', cascade='all, delete-orphan'
    ))
    action_type = Column(db.String(255))
    action_detail = Column(JSON)
    taken_at = Column(db.DateTime, default=datetime.datetime.utcnow())

    taken_by = ReferenceCol('users', ondelete='SET NULL', nullable=True)
    taken_by_user = db.relationship('User', backref=backref(
        'contract_stage_actions', lazy='dynamic'
    ), foreign_keys=taken_by)

    def __unicode__(self):
        return self.action_type

    @property
    def non_null_items(self):
        '''Return the filtered actions where the action's value is not none
        '''
        return dict((k, v) for (k, v) in self.action_detail.items() if v is not None)

    @property
    def non_null_items_count(self):
        '''Return a count of the non-null items in an action's detailed log
        '''
        return len(self.non_null_items)

    @property
    def is_start_type(self):
        '''Return true if the action type is either entered or reverted
        '''
        return self.action_type in ['entered', 'reversion']

    @property
    def is_exited_type(self):
        '''Return true if the action type is exited
        '''
        return self.action_type == 'exited'

    @property
    def is_other_type(self):
        '''Return true if the action type is not start or exited type
        '''
        return not any([self.is_start_type, self.is_exited_type])

    def get_sort_key(self):
        '''Return the date field for sorting the action log

        See Also:
            :py:meth:`purchasing.data.contracts.ContractBase.filter_action_log`
        '''
        # if we are reversion, we need to get the timestamps from there
        if self.is_start_type or self.is_exited_type:
            return datetime.datetime.strptime(
                self.action_detail['timestamp'],
                '%Y-%m-%dT%H:%M:%S'
            )
        # otherwise, return the taken_at time
        else:
            return self.taken_at
