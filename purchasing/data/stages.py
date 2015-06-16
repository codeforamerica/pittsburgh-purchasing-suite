# -*- coding: utf-8 -*-

from purchasing.data.models import Stage, StageProperty, ContractStage
from purchasing.data.contracts import get_one_contract

def create_new_stage(stage_data):
    '''Create a new stage.

    Creates a new stage from the passed stage_data
    and returns the created stage object.
    '''
    properties = stage_data.pop('properties', [])
    stage = Stage.create(**stage_data)
    for property in properties:
        property.update({'stage_id': stage.id})
        StageProperty.create(**property)

    return stage

def update_stage(stage_id, stage_data):
    '''Updates stage data.

    Takes an individual stage and updates it with
    the stage data. Returns the updated stage.
    '''
    stage = get_one_stage(stage_id)
    stage.update(**stage_data)
    return stage

def update_stage_property(stage_property_id, property_data):
    '''Updates stage property data.

    Takes a dictionary of stage property data and
    updates the individual property
    '''
    stage_property = StageProperty.query.get(stage_property_id)
    stage_property.update(**property_data)
    return stage_property

def delete_stage(stage_id):
    '''Deletes a stage and any associated properties
    '''
    stage = get_one_stage(stage_id)
    stage.delete()
    return True

def get_one_stage(stage_id):
    '''Takes a stage ID and returns the associated stage object
    '''
    return Stage.query.get(stage_id)

def get_all_stages():
    '''Returns one page's worth of stages.
    '''
    return Stage.query.all()

def transition_stage(contract_id, destination=None, contract=None, stages=None):
    '''Transitions a contract from one stage to another

    Stages are organized a bit like a finite state machine. The "flow"
    dictates the order of the states. Because these are linear, we can
    get everything that we need out of the properties of the contract.

    If there is a "destination" stage, then we need to transition all
    the way to that stage, marking everything in-between as complete.

    Otherwise, if the contract doesn't have a current stage, it should
    enter the first stage of its flow. If it does, then it should exit
    that and and move into the next stage. If we are trying to transition
    out of the final stage of the flow, then we need to create a clone
    of the contract.

    Optionally, takes the actual contract object and stages. We can
    always grab the objects if we need them, but they are optional
    to increase speed.
    '''
    # grab the contract
    contract = contract if contract else get_one_contract(contract_id)
    stages = stages if stages else contract.flow.stage_order

    # implement the case where we have a final destination in mind
    if destination:
        # TODO: handle going backwards (delete exit times)
        pass

    # implement first case -- current stage is none
    elif contract.current_stage is None:
        stage_to_update = ContractStage.query.filter(
            ContractStage.contract_id == contract_id,
            ContractStage.stage_id == stages[0]
        ).first()
        stage_to_update.enter()
        return stage_to_update, contract

    # implement the second case -- current stage is last stage
    elif contract.current_stage_id == contract.flow.stage_order[-1]:
        import pdb; pdb.set_trace()

    # implement final case -- transitioning to new stage
    else:
        current_stage_idx = stages.index(contract.current_stage_id)

        stages_to_transition = ContractStage.query.filter(
            ContractStage.contract_id == contract_id,
            ContractStage.stage_id.in_([
                stages[current_stage_idx],
                stages[current_stage_idx + 1]
            ])
        ).order_by(ContractStage.id).all()

        import pdb; pdb.set_trace()

        # exit the current stage
        stages_to_transition[0].exit()
        # enter the new stage
        stages_to_transition[1].enter()

        return stages_to_transition[1], contract

