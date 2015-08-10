# -*- coding: utf-8 -*-

import datetime

from purchasing.database import db
from purchasing.data.models import (
    Flow, Stage, ContractStage, ContractBase,
    ContractStageActionItem
)
from purchasing.data.stages import transition_stage

def create_new_flow(flow_data):
    '''
    Creates a new flow from the passed flow_data
    and returns the created flow object.
    '''
    try:
        validate_stages_exist(flow_data.get('stage_order', []))
        flow = Flow.create(**flow_data)
        return flow
    except Exception, e:
        db.session.rollback()
        raise e

def update_flow(flow_id, flow_data):
    '''
    Takes an individual flow and updates it with
    the flow data. Returns the updated flow.
    '''
    try:
        flow = get_one_flow(flow_id)
        validate_stages_exist(flow_data.get('stage_order', []))
        flow.update(**flow_data)
        return flow
    except Exception, e:
        db.session.rollback()
        raise e

def delete_flow(flow_id):
    '''
    Takes a flow ID and deletes it. Returns True
    '''
    flow = get_one_flow(flow_id)
    flow.delete()
    return True

def get_one_flow(flow_id):
    '''
    Takes a flow ID and returns the associated flow object
    '''
    return Flow.query.get(flow_id)

def get_all_flows():
    '''
    Returns a list of flows.
    TODO: Paginate this
    '''
    return Flow.query.all()

def validate_stages_exist(stage_order):
    if len(stage_order) == 0:
        return True

    existing_stage_query = db.session.query(Stage.id).filter(Stage.id.in_(stage_order))

    if existing_stage_query.count() == len(stage_order):
        return True
    else:
        not_exist = ','.join([i for i in stage_order if i not in existing_stage_query.all()])
        raise Exception('Stage in stage_order must exist. These stages do not exist {stages}'.format(stages=not_exist))

def create_contract_stages(flow_id, contract_id, contract=None):
    '''Creates new rows in contract_stage table.

    Extracts the rows out of the given flow, and creates new rows
    in the contract_stage table for each of them.
    '''
    contract = contract if contract else ContractBase.query.get(contract_id)
    stages = get_one_flow(flow_id).stage_order
    contract_stages = []
    for stage_id in stages:
        try:
            contract_stages.append(ContractStage.create(
                contract_id=contract_id,
                flow_id=flow_id,
                stage_id=stage_id,
            ))

        except Exception:
            raise

    contract.flow_id = flow_id
    db.session.commit()

    return stages, contract_stages

def switch_flow(new_flow_id, contract_id, user):
    '''Switch the contract's progress from one flow to another

    Instead of trying to do anything too smart, we prefer instead
    to be dumb -- it is better to force the user to click ahead
    through a bunch of stages than it is to incorrectly fast-forward
    them to an incorrect state.

    There are three concrete actions here:
        1. Rebuild our flow/stage model for the new order.
        2. Attach the complete log of the old flow into the first stage
          of the new order.
        3. Strip the contract's current stage id.
        4. Transition into the first stage of the new order. This will
          ensure that everything is being logged in the correct order.
    '''
    # get our contract and its complete action history
    contract = ContractBase.query.get(contract_id)
    old_flow = contract.flow.flow_name
    old_action_log = contract.build_complete_action_log()

    # create the new stages
    new_stages, new_contract_stages = create_contract_stages(
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
            'old_flow_actions': [i.as_dict() for i in old_action_log]
        }
    )
    db.session.add(switch_log)
    db.session.commit()

    # remove the current_stage_id from the contract
    # so we can start the new flow
    contract.current_stage_id = None

    # transition into the first stage of the new flow
    new_stage, new_contract, _ = transition_stage(
        contract.id, user, contract=contract, stages=new_stages
    )
    db.session.commit()
    return new_stage
