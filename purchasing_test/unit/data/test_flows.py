# -*- coding: utf-8 -*-

from sqlalchemy.exc import IntegrityError
from purchasing.database import db
from purchasing.data.models import Flow, Stage
from purchasing.data.flows import (
    create_new_flow, update_flow,
    delete_flow, get_all_flows
)

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import insert_a_stage, insert_a_flow

class FlowTest(BaseTestCase):
    def setUp(self):
        super(FlowTest, self).setUp()
        stage1 = insert_a_stage()
        stage2 = insert_a_stage()
        self.stage_ids = [stage1.id, stage2.id]

    def test_create_new_flow(self):
        # assert we can create a flow with proper ids
        flow_data = dict(
            flow_name='flow',
            stage_order=self.stage_ids
        )

        flow = create_new_flow(flow_data)

        self.assertEquals(Flow.query.count(), 1)
        self.assertEquals(Flow.query.first().flow_name, flow.flow_name)

        # assert we can't create a flow with a duplicate name
        self.assertRaises(IntegrityError, create_new_flow, dict(
            flow_name=flow.flow_name
        ))

        # rollback the database transaction
        db.session.rollback()

        # assert we can't create the flow if the stage ids are not included
        # self.assertRaises(Exception, create_new_flow, dict(
        #     flow_name='flow2',
        #     stage_order=[999]
        # ))

    def test_update_flow(self):
        flow = insert_a_flow(stage_ids=self.stage_ids)
        self.assertEquals(Flow.query.first().flow_name, flow.flow_name)

        update_flow(flow.id, {'flow_name': 'updated'})
        self.assertEquals(Flow.query.first().flow_name, 'updated')

    def test_delete_flow(self):
        flow = insert_a_flow(stage_ids=self.stage_ids)
        self.assertEquals(Flow.query.count(), 1)

        delete_flow(flow.id)
        self.assertEquals(Flow.query.count(), 0)
        self.assertEquals(Stage.query.count(), 2)

    def test_get_all_flows(self):
        insert_a_flow(name='one')
        insert_a_flow(name='two')
        insert_a_flow(name='three')

        self.assertEquals(len(get_all_flows()), 3)

    def test_delete_stage_updates_flow(self):
        pass
