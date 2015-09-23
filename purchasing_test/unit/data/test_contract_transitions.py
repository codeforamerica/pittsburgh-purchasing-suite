# -*- coding: utf-8 -*-

from mock import Mock, patch

from purchasing.opportunities.models import Opportunity
from purchasing.data import contracts, flows, stages
from purchasing.data.contract_stages import ContractStage
from purchasing.users import models

from purchasing_test.factories import (
    ContractBaseFactory, UserFactory, ContractPropertyFactory,
    FlowFactory, StageFactory
)
from purchasing_test.unit.data.test_contract_base import ContractObjectTestBase

class TestContractTransition(ContractObjectTestBase):
    def setUp(self):
        super(TestContractTransition, self).setUp()
        self.stage1 = StageFactory.build(name='stage 1')
        self.stage2 = StageFactory.build(name='stage 2')
        self.stage3 = StageFactory.build(name='stage 3')

        self.flow1 = FlowFactory.build(
            flow_name='flow 1', stage_order=[self.stage1.id, self.stage2.id, self.stage3.id]
        )
        self.flow2 = FlowFactory.build(
            flow_name='flow 2', stage_order=[self.stage1.id, self.stage2.id, self.stage3.id]
        )

        self.user = UserFactory.build()

        self.active_contract.flow = self.flow1

    @patch('purchasing.data.contracts.ContractBase._transition_to_last')
    @patch('purchasing.data.contracts.ContractBase._transition_to_next')
    @patch('purchasing.data.contracts.ContractBase._transition_to_first')
    def test_transition(self, first, _next, last):
        '''Test that transition calls the right methods in the right circumstances
        '''
        self.assertTrue(self.active_contract.current_stage_id is None)
        self.active_contract.transition(self.user)
        self.assertTrue(first.called)

        self.active_contract.current_stage_id = self.stage1.id
        self.active_contract.transition(self.user)
        self.assertTrue(_next.called)

        self.active_contract.current_stage_id = self.stage2.id
        self.active_contract.transition(self.user)
        self.assertTrue(_next.called)

        self.active_contract.current_stage_id = self.stage3.id
        self.active_contract.transition(self.user)
        self.assertTrue(last.called)

        self.assertEquals(first.call_count, 1)
        self.assertEquals(_next.call_count, 2)
        self.assertEquals(last.call_count, 1)

    def test_transition_start(self):
        _get = Mock(return_value=ContractStage(stage=self.stage1))
        ContractStage.get_one = _get

        self.assertTrue(self.active_contract.current_stage_id is None)
        action = self.active_contract.transition(self.user)
        self.assertEquals(_get.call_count, 1)
        self.assertEquals(len(action), 1)
        self.assertEquals(action[0].action_type, 'entered')
        self.assertEquals(self.active_contract.current_stage_id, self.stage1.id)

    def test_transition_next(self):
        _get = Mock()
        _get.side_effect = [ContractStage(stage=self.stage1), ContractStage(stage=self.stage2)]
        ContractStage.get_one = _get

        self.active_contract.current_stage_id = self.stage1.id
        self.active_contract.current_stage = self.stage1

        action = self.active_contract.transition(self.user)
        self.assertEquals(_get.call_count, 2)
        self.assertEquals(len(action), 2)
        self.assertEquals(action[0].action_type, 'exited')
        self.assertEquals(action[1].action_type, 'entered')
        self.assertEquals(self.active_contract.current_stage_id, self.stage2.id)

    @patch('purchasing.data.contracts.ContractBase.complete')
    def test_transition_last(self, complete):
        _get = Mock(return_value=ContractStage(stage=self.stage1))
        ContractStage.get_one = _get

        self.active_contract.parent = ContractBaseFactory.build(description='test')
        self.active_contract.current_stage_id = self.stage3.id
        self.active_contract.current_stage = self.stage3

        action = self.active_contract.transition(self.user)
        self.assertEquals(_get.call_count, 1)
        self.assertEquals(len(action), 1)
        self.assertEquals(action[0].action_type, 'exited')
        self.assertTrue(complete.called_once)

    def test_transition_backward(self):
        _get = Mock(return_value=[ContractStage(stage=self.stage1), ContractStage(stage=self.stage2)])
        ContractStage.get_multiple = _get

        self.active_contract.current_stage_id = self.stage2.id
        self.active_contract.current_stage = self.stage2

        action = self.active_contract.transition(self.user, destination=self.stage1.id)
        self.assertEquals(_get.call_count, 1)
        self.assertEquals(len(action), 1)
        self.assertEquals(action[0].action_type, 'reversion')
        self.assertTrue(_get.called_once)
        self.assertEquals(self.active_contract.current_stage_id, self.stage1.id)

