# -*- coding: utf-8 -*-

from purchasing.data.flows import Flow
from purchasing.data.stages import Stage
from purchasing_test.integration.conductor.test_conductor import TestConductorSetup

class TestConductorFlows(TestConductorSetup):
    render_template = True

    def test_conductor_flow_creation(self):
        self.assertEquals(Flow.query.count(), 3)
        no_title = self.client.post('/conductor/flow/new', data={
            'stage_order-0': self.stage3.id,
            'stage_order-1': self.stage1.id
        })
        self.assertTrue('is required' in no_title.data)

        duplicate_stages = self.client.post('/conductor/flow/new', data={
            'flow_name': 'a new flow',
            'stage_order-0': self.stage1.id,
            'stage_order-1': self.stage1.id
        })
        self.assertTrue('You cannot have duplicate stages' in duplicate_stages.data)

        no_stages = self.client.post('/conductor/flow/new', data={
            'flow_name': 'a new flow',
            'stage_order-0': 'None',
        })
        self.assertTrue('You must have at least one stage!' in no_stages.data)

        duplicate_title = self.client.post('/conductor/flow/new', data={
            'flow_name': self.flow.flow_name,
            'stage_order-0': self.stage1.id,
        })
        self.assertTrue('A flow with that name already exists!' in duplicate_title.data)

        self.assertEquals(Flow.query.count(), 3)

        self.client.post('/conductor/flow/new', data={
            'flow_name': 'great and new!',
            'stage_order-0': self.stage2.id,
            'stage_order-1': self.stage1.id
        })

        self.assertEquals(Flow.query.count(), 4)

    def test_conductor_flow_new_stage_add(self):
        self.assertEquals(Flow.query.count(), 3)
        self.assertEquals(Stage.query.count(), 3)

        self.client.post('/conductor/flow/new', data={
            'flow_name': 'great and new!',
            'stage_order-0': self.stage2.id,
            'stage_order-1': 'Wow this is super great and new!'
        })

        self.assertEquals(Flow.query.count(), 4)
        self.assertEquals(Stage.query.count(), 4)

    def test_conductor_flow_browse(self):
        browse = self.client.get('/conductor/flows')
        self.assert200(browse)
        self.assertEquals(len(self.get_context_variable('flows')), 3)

    def test_conductor_edit(self):
        self.assertEquals(Flow.query.count(), 3)
        flow_url = '/conductor/flow/{}'.format(self.flow.id)
        self.assert200(self.client.get(flow_url))

        self.client.post(flow_url, data={
            'id': self.flow.id,
            'flow_name': 'a new flow name',
            'is_archived': True
        })

        self.assertEquals(Flow.query.count(), 3)
        self.assertEquals(Flow.query.get(self.flow.id).flow_name, 'a new flow name')

    def test_conductor_start_archived(self):
        self.client.post('/conductor/flow/{}'.format(self.flow.id), data={
            'id': self.flow.id,
            'flow_name': self.flow.flow_name,
            'is_archived': True
        })

        self.client.get('/conductor/contract/new')
        # should have three choices: 1 blank and two non-archived
        flow_choices = list(self.get_context_variable('form').flow.iter_choices())
        self.assertEquals(len(flow_choices), 3)
        self.assertTrue(
            self.flow.flow_name not in [i[1] for i in flow_choices]
        )
