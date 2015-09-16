# -*- coding: utf-8 -*-

import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from sqlalchemy.dialects.postgres import ARRAY

from purchasing.database import db, Model, Column
from purchasing.data.contracts import ContractBase
from purchasing.data.contract_stages import ContractStage, ContractStageActionItem

class Flow(Model):
    __tablename__ = 'flow'

    id = Column(db.Integer, primary_key=True, index=True)
    flow_name = Column(db.Text, unique=True)
    contract = db.relationship('ContractBase', backref='flow', lazy='subquery')
    stage_order = Column(ARRAY(db.Integer))

    def __unicode__(self):
        return self.flow_name

    @classmethod
    def all_flow_query_factory(cls):
        return cls.query

def create_contract_stages(flow_id, contract_id, contract=None):
    '''Creates new rows in contract_stage table.

    Extracts the rows out of the given flow, and creates new rows
    in the contract_stage table for each of them.
    '''
    revert = False
    contract = contract if contract else ContractBase.query.get(contract_id)
    stages = Flow.query.get(flow_id).stage_order
    contract_stages = []
    for stage_id in stages:
        try:
            contract_stages.append(ContractStage.create(
                contract_id=contract_id,
                flow_id=flow_id,
                stage_id=stage_id,
            ))

        except (IntegrityError, FlushError):
            revert = True
            db.session.rollback()
            stage = ContractStage.query.filter(
                ContractStage.contract_id == contract_id,
                ContractStage.flow_id == flow_id,
                ContractStage.stage_id == stage_id
            ).first()
            if stage:
                contract_stages.append(stage)
            else:
                raise IntegrityError

        except Exception:
            raise

    contract.flow_id = flow_id
    db.session.commit()

    return stages, contract_stages, revert

def switch_flow(new_flow_id, contract_id, user):
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
    '''
    # get our contract and its complete action history
    contract = ContractBase.query.get(contract_id)
    old_flow = contract.flow.flow_name
    old_action_log = contract.build_complete_action_log()

    # fully revert all used stages in the old flow
    for contract_stage in ContractStage.query.filter(
        ContractStage.contract_id == contract_id,
        ContractStage.flow_id == contract.flow_id,
        ContractStage.entered != None
    ).all():
        contract_stage.full_revert()
        contract_stage.strip_actions()

    db.session.commit()

    # create the new stages
    new_stages, new_contract_stages, revert = create_contract_stages(
        new_flow_id, contract_id, contract=contract
    )

    # log that we are switching flows into the first stage
    switch_log = ContractStageActionItem(
        contract_stage_id=new_contract_stages[0].id, action_type='flow_switch',
        taken_by=user.id, taken_at=datetime.datetime.now(),
        action_detail={
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'type': 'flow_switched', 'old_flow': old_flow,
            'new_flow': contract.flow.flow_name,
            'old_flow_actions': [i.as_dict() for i in old_action_log]
        }
    )
    db.session.add(switch_log)
    db.session.commit()

    # remove the current_stage_id from the contract
    # so we can start the new flow
    contract.current_stage_id = None
    contract.flow_id = new_flow_id

    destination = None
    if revert:
        destination = new_stages[0]

    # transition into the first stage of the new flow
    actions = contract.transition(user, destination=destination)
    for i in actions:
        db.session.add(i)

    db.session.commit()
    return new_contract_stages[0], contract
