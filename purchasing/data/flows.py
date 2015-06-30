# -*- coding: utf-8 -*-

from purchasing.database import db
from purchasing.data.models import Flow, Stage, ContractStage, ContractBase

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
    for stage in stages:
        try:
            ContractStage.create(
                contract_id=contract_id,
                stage_id=stage,
            )

        except Exception:
            raise

    contract.flow_id = flow_id
    db.session.commit()

    return stages
