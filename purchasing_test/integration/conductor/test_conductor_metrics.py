# -*- coding: utf-8 -*-

import datetime
from collections import defaultdict
from purchasing.database import db
from purchasing_test.integration.conductor.test_conductor import TestConductorSetup
from purchasing_test.util import insert_a_contract

class TestConductorMetrics(TestConductorSetup):
    render_templates = True

    def setUp(self):
        super(TestConductorMetrics, self).setUp()
        self.assign_contract()

        transition_url_1 = self.build_detail_view(self.contract1) + '/transition'

        self.assign_contract(contract=self.contract2)
        transition_url_2 = self.build_detail_view(self.contract2) + '/transition'

        for stage in self.flow.stage_order:
            self.client.get(transition_url_1)
            self.client.get(transition_url_2)

    def test_metrics_index(self):
        self.assert200(self.client.get('/conductor/metrics/'))

        self.logout_user()
        self.assertEquals(self.client.get('/conductor/metrics/').status_code, 302)

    def test_metrics_tsv_download(self):
        request = self.client.get('/conductor/metrics/download/{}'.format(self.flow.id), follow_redirects=True)
        self.assertEquals(request.mimetype, 'text/tsv')
        self.assertEquals(
            request.headers.get('Content-Disposition'),
            'attachment; filename=conductor-{}-metrics.tsv'.format(self.flow.flow_name)
        )

        tsv_data = request.data.split('\n')[:-1]

        # we should have two rows plus the header
        self.assertEquals(len(tsv_data), 3)
        for row in tsv_data[1:]:
            # there should be four metadata columns plus the number of stages
            self.assertEquals(len(row.split('\t')), len(self.flow.stage_order) + 4)

    def test_metrics_tsv_download_all(self):
        insert_a_contract(
            contract_type=self.county_type, description='scuba supplies 2', financial_id=789,
            expiration_date=datetime.date.today(), properties=[{'key': 'Spec Number', 'value': '789'}],
            is_visible=True, department=self.department, is_archived=False
        )
        db.session.commit()
        request = self.client.get('/conductor/metrics/download/all', follow_redirects=True)
        self.assertEquals(request.mimetype, 'text/tsv')
        self.assertEquals(
            request.headers.get('Content-Disposition'),
            "attachment; filename=conductor-all-{}.tsv".format(datetime.date.today())
        )

        tsv_data = request.data.split('\n')[:-1]
        self.assertEquals(len(tsv_data), 4)
        status = defaultdict(int)
        for i in tsv_data[1:]:
            status[i.split('\t')[-1]] += 1

        self.assertEquals(status['not started'], 1)
        self.assertEquals(status['started'], 2)

    def test_metrics_data(self):
        self.assert200(self.client.get('/conductor/metrics/overview/{}/data'.format(self.flow.id)))
