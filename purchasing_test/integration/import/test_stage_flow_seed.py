# -*- coding: utf-8 -*-

from purchasing.opportunities.models import Opportunity
from purchasing.data.stages import Stage
from purchasing.data.flows import Flow

from purchasing_test.test_base import BaseTestCase

from purchasing.data.importer.stages_and_flows import seed_stages_and_flows

class TestStageAndFlowSeed(BaseTestCase):
    def test_stage_and_flow_seed(self):
        seed_stages_and_flows()

        self.assertEquals(Flow.query.count(), 1)
        self.assertEquals(Stage.query.count(), 3)

        for i in Stage.query.all():
            self.assertTrue(i.id in Flow.query.first().stage_order)
