# -*- coding: utf-8 -*-

from purchasing.data.models import Flow

def create_new_flow(flow_data):
    '''
    Creates a new flow from the passed flow_data
    and returns the created flow object.
    '''
    flow = Flow.create(**flow_data)
    return flow

def update_flow(flow_id, flow_data):
    '''
    Takes an individual flow and updates it with
    the flow data. Returns the updated flow.
    '''
    flow = get_one_flow(flow_id)
    flow.update(**flow_data)
    return flow

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
