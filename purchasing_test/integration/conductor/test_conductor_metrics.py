# -*- coding: utf-8 -*-

from purchasing_test.integration.conductor.test_conductor import TestConductorSetup

class TestConductorMetrics(TestConductorSetup):
    render_templates = True

    def test_metrics_index(self):
        self.assert200(self.client.get('/conductor/metrics/'))

        self.logout_user()
        self.assertEquals(self.client.get('/conductor/metrics/').status_code, 302)

    def test_metrics_tsv_download(self):
        self.assign_contract()
        transition_url_1 = self.build_detail_view(self.contract1) + '/transition'

        self.assign_contract(contract=self.contract2)
        transition_url_2 = self.build_detail_view(self.contract2) + '/transition'

        # transition all the way through both stages
        for stage in self.flow.stage_order:
            self.client.get(transition_url_1)
            self.client.get(transition_url_2)

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
