# -*- coding: utf-8 -*-

from purchasing.data.models import Stage, StageProperty

def create_new_stage(stage_data):
    '''
    Creates a new stage from the passed stage_data
    and returns the created stage object.
    '''
    properties = stage_data.pop('properties', [])
    stage = Stage.create(**stage_data)
    for property in properties:
        StageProperty.create(**property)

    return stage

def update_stage(stage_id, stage_data):
    '''
    Takes an individual stage and updates it with
    the stage data. Returns the updated stage.
    '''
    stage = get_one_stage(stage_id)
    stage.update(**stage_data)
    return stage

def update_stage_property(stage_id, stage_property_id, property_data):
    '''
    Takes a dictionary of stage property data and
    updates the individual property
    '''
    stage_property = StageProperty.query.get(stage_property_id)
    stage_property.update(**property_data)
    return stage_property

def delete_stage(stage_id):
    '''
    Deletes a stage and any associated properties
    '''
    stage = get_one_stage(stage_id)
    stage.delete()
    return True

def get_one_stage(stage_id):
    '''
    Takes a stage ID and returns the associated stage object
    '''
    return Stage.query.get(stage_id)

def get_all_stages(page):
    '''
    Returns one page's worth of stages. The length of a
    page is configurable via the settings and defaults to 20
    '''
    return Stage.query.all()
