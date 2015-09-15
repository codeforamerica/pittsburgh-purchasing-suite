# -*- coding: utf-8 -*-

import datetime

from sqlalchemy.schema import Sequence
from sqlalchemy.orm import backref
from sqlalchemy.dialects.postgresql import JSON

from purchasing.database import Model, db, Column, ReferenceCol

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

    @classmethod
    def get_one(cls, contract_id, flow_id, stage_id):
        return cls.query.filter(
            cls.contract_id == contract_id,
            cls.stage_id == stage_id,
            cls.flow_id == flow_id
        ).first()

    @classmethod
    def get_multiple(cls, contract_id, flow_id, stage_ids):
        return cls.query.filter(
            cls.contract_id == contract_id,
            cls.stage_id.in_(stage_ids),
            cls.flow_id == flow_id
        ).order_by(cls.id).all()

    def enter(self):
        '''Enter the stage at this point
        '''
        self.entered = datetime.datetime.now()

    def log_enter(self, user):
        self.enter()
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

    def exit(self):
        '''Exit the stage
        '''
        self.exited = datetime.datetime.now()

    def log_exit(self, user):
        self.exit()
        return ContractStageActionItem(
            contract_stage_id=self.id, action_type='exited',
            taken_by=user.id, taken_at=datetime.datetime.now(),
            action_detail={
                'timestamp': self.exited.strftime('%Y-%m-%dT%H:%M:%S'),
                'date': self.exited.strftime('%Y-%m-%d'),
                'type': 'exited', 'label': 'Completed work',
                'stage_name': self.stage.name
            }
        )

    def log_reopen(self, user):
        return ContractStageActionItem(
            contract_stage_id=self.id, action_type='reversion',
            taken_by=user.id, taken_at=datetime.datetime.now(),
            action_detail={
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'type': 'reopened', 'label': 'Restarted work',
                'stage_name': self.stage.name
            }
        )

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
    ), foreign_keys=taken_by)

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
