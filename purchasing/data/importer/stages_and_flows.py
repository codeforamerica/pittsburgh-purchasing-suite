# -*- coding: utf-8 -*-

from purchasing.database import db

from purchasing.data.stages import Stage
from purchasing.data.flows import Flow

def seed_stages_and_flows():
    '''Seed one flow with three stages named "one", "two", and "three"
    '''
    stage1 = Stage.create(
        name='one', post_opportunities=True,
        default_message='This is a default message for stage one!'
    )

    stage2 = Stage.create(
        name='two', post_opportunities=True,
    )

    stage3 = Stage.create(
        name='three', post_opportunities=True
    )

    Flow.create(
        flow_name='Default Flow', stage_order=[stage1.id, stage2.id, stage3.id]
    )
    db.session.commit()
