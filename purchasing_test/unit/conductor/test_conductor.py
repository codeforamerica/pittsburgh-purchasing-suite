# -*- coding: utf-8 -*-

import json
import unittest
import datetime
import urllib2
from mock import Mock, patch

from purchasing.data.models import (
    ContractStage, ContractBase, ContractStageActionItem
)
from purchasing.extensions import mail

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_contract, insert_a_stage, insert_a_flow,
    insert_a_role, insert_a_user
)

class TestConductor(BaseTestCase):
    render_templates = True

    def setUp(self):
        super(TestConductor, self).setUp()
        # create a conductor and general staff person
        self.conductor_role_id = insert_a_role('conductor')
        self.staff_role_id = insert_a_role('staff')
        self.conductor = insert_a_user(role=self.conductor_role_id)
        self.staff = insert_a_user(email='foo2@foo.com', role=self.staff_role_id)

        # create three stages, and set up a flow between them
        self.stage1 = insert_a_stage(name='stage1', send_notifs=True, post_opportunities=True)
        self.stage2 = insert_a_stage(name='stage2', send_notifs=True, post_opportunities=False)
        self.stage3 = insert_a_stage(name='stage3', send_notifs=False, post_opportunities=False)

        self.flow = insert_a_flow(stage_ids=[self.stage1.id, self.stage2.id, self.stage3.id])

        # create two contracts
        self.contract1 = insert_a_contract(
            contract_type='County', description='scuba supplies', financial_id=123,
            properties=[{'key': 'Spec Number', 'value': '123'}]
        )
        self.contract2 = insert_a_contract(
            contract_type='County', description='scuba repair', financial_id=456,
            properties=[{'key': 'Spec Number', 'value': '456'}]
        )

        self.login_user(self.conductor)
        self.detail_view = '/conductor/contract/{}/stage/{}'

    def tearDown(self):
        super(TestConductor, self).tearDown()

    def assign_contract(self):
        return self.client.get('/conductor/contract/{}/assign/{}/flow/{}'.format(
            self.contract1.id, self.conductor.id, self.flow.id
        ))

    def get_current_contract_stage_id(self, contract, old_stage=None):
        if not contract.current_stage_id:
            return -1

        if not old_stage:
            stage = ContractStage.query.filter(
                contract.current_stage_id == ContractStage.stage_id,
                contract.id == ContractStage.contract_id
            ).first()
        else:
            stage = ContractStage.query.filter(
                old_stage.id == ContractStage.stage_id,
                contract.id == ContractStage.contract_id
            ).first()

        return stage.id

    def build_detail_view(self, contract, old_stage=None):
        return self.detail_view.format(
            contract.id, self.get_current_contract_stage_id(contract, old_stage)
        )

    def test_conductor_contract_list(self):
        '''Test basic conductor list view
        '''
        index_view = self.client.get('/conductor', follow_redirects=True)
        self.assert200(index_view)
        self.assert_template_used('conductor/index.html')

        # we have 2 contracts
        contracts = self.get_context_variable('contracts')
        self.assertEquals(len(contracts), 2)
        # neither contract is assigned
        for contract in contracts:
            self.assertTrue(contract.assigned is None)

        # we can't get to the page normally
        self.logout_user()
        index_view = self.client.get('/conductor', follow_redirects=True)
        self.assert200(index_view)
        # it should redirect us to the home page
        self.assert_template_used('public/home.html')

        self.login_user(self.staff)
        index_view = self.client.get('/conductor', follow_redirects=True)
        self.assert200(index_view)
        # it should redirect us to the home page
        self.assert_template_used('public/home.html')

    def test_conductor_contract_assign(self):
        '''Test contract assignment via conductor
        '''
        self.assertEquals(ContractStage.query.count(), 0)

        assign = self.assign_contract()

        self.assertEquals(ContractStage.query.count(), len(self.flow.stage_order))
        self.assertEquals(self.contract1.current_stage_id, self.flow.stage_order[0])
        self.assertEquals(self.contract1.assigned_to, self.conductor.id)

        self.assertEquals(assign.status_code, 302)
        self.assert_flashes('Successfully assigned to {}!'.format(self.conductor.email), 'alert-success')
        self.assertEquals(assign.location, 'http://localhost/conductor/')

        # re-assigning shouldn't cause problems
        self.assign_contract()

    def test_conductor_contract_detail_view(self):
        '''Test basic conductor detail view
        '''
        self.assert404(self.client.get(self.detail_view.format(999, 999)))

        self.assign_contract()

        detail_view_url = self.build_detail_view(self.contract1)

        detail = self.client.get(self.build_detail_view(self.contract1))
        self.assert200(detail)
        self.assert_template_used('conductor/detail.html')
        self.assertEquals(self.get_context_variable('active_tab'), '#activity')
        self.assertEquals(
            self.get_context_variable('current_stage').id,
            self.get_context_variable('active_stage').id
        )
        self.assertEquals(len(self.get_context_variable('actions')), 2)

        # make sure the redirect works
        redir = self.client.get('/conductor/contract/{}'.format(self.contract1.id))
        self.assertEquals(redir.status_code, 302)
        self.assertEquals(redir.location, 'http://localhost' + detail_view_url)

        self.logout_user()

        # make sure we can't get to it unless we are the right user
        detail = self.client.get(detail_view_url, follow_redirects=True)
        self.assert200(detail)
        # it should redirect us to the home page
        self.assert_template_used('public/home.html')

        self.login_user(self.staff)
        detail = self.client.get(detail_view_url, follow_redirects=True)
        self.assert200(detail)
        # it should redirect us to the home page
        self.assert_template_used('public/home.html')

    def test_conductor_contract_transition(self):
        '''Test conductor stage transition
        '''
        self.assign_contract()

        transition_url = self.build_detail_view(self.contract1) + '?transition=true'
        transition = self.client.get(transition_url)
        self.assertEquals(transition.status_code, 302)
        self.assertEquals(
            transition.location, 'http://localhost' + self.build_detail_view(self.contract1)
        )
        new_page = self.client.get(self.build_detail_view(self.contract1))
        self.assertTrue('<a href="#post" aria-controls="post" role="tab" data-toggle="tab">' not in new_page.data)

        contract_stages = ContractStage.query.all()
        for stage in contract_stages:
            if stage.id == self.stage1.id:
                self.assertTrue(stage.entered is not None and stage.exited is not None)
            elif stage.id == self.stage2.id:
                self.assertTrue(stage.entered is not None and stage.exited is None)
            elif stage.id == self.stage3.id:
                self.assertTrue(stage.entered is None and stage.exited is None)

    def test_conductor_directed_transition(self):
        '''Test conductor stage transition backwards/to specific point
        '''
        self.assign_contract()
        self.assertEquals(ContractStageActionItem.query.count(), 0)

        # transition to the third stage
        transition_url = self.build_detail_view(self.contract1) + '?transition=true'
        self.client.get(transition_url)
        self.client.get(transition_url)

        self.assertEquals(ContractBase.query.get(1).current_stage_id, self.stage3.id)

        revert_url = self.build_detail_view(self.contract1) + '?transition=true&destination={}'
        # revert to the original stage
        self.client.get(revert_url.format(self.stage1.id))

        self.assertEquals(ContractStageActionItem.query.count(), 7)
        # there should be 3 for stage 1 & 2 (enter, exit, reopen)
        self.assertEquals(ContractStageActionItem.query.join(ContractStage).filter(
            ContractStage.stage_id == self.stage1.id
        ).count(), 3)

        self.assertEquals(ContractStageActionItem.query.join(ContractStage).filter(
            ContractStage.stage_id == self.stage2.id
        ).count(), 3)

        self.assertEquals(ContractStageActionItem.query.join(ContractStage).filter(
            ContractStage.stage_id == self.stage3.id
        ).count(), 1)

        self.assertEquals(ContractBase.query.get(1).current_stage_id, self.stage1.id)
        self.assertTrue(ContractStage.query.filter(ContractStage.stage_id == self.stage1.id).first().entered is not None)
        self.assertTrue(ContractStage.query.filter(ContractStage.stage_id == self.stage2.id).first().entered is None)
        self.assertTrue(ContractStage.query.filter(ContractStage.stage_id == self.stage3.id).first().entered is None)

        self.assertTrue(ContractStage.query.filter(ContractStage.stage_id == self.stage1.id).first().exited is None)
        self.assertTrue(ContractStage.query.filter(ContractStage.stage_id == self.stage2.id).first().exited is None)
        self.assertTrue(ContractStage.query.filter(ContractStage.stage_id == self.stage3.id).first().exited is None)

    def test_conductor_link_directions(self):
        '''Test that we can access completed stages but not non-started ones
        '''
        self.assign_contract()
        self.client.get(self.detail_view.format(self.contract1.id, self.stage1.id) + '?transition=true')

        # assert the current stage is stage 2
        redir = self.client.get('/conductor/contract/{}'.format(self.contract1.id))
        self.assertEquals(redir.status_code, 302)
        self.assertEquals(redir.location, 'http://localhost' + self.build_detail_view(self.contract1))
        # assert we can/can't go the correct locations
        old_view = self.client.get(self.build_detail_view(self.contract1, old_stage=self.stage1))
        self.assert200(old_view)
        self.assertTrue('You are viewing an already-completed stage.' in old_view.data)
        self.assert200(self.client.get(self.build_detail_view(self.contract1, old_stage=self.stage2)))
        self.assert404(self.client.get(self.build_detail_view(self.contract1, old_stage=self.stage3)))

    def test_conductor_contract_complete(self):
        '''Test completing an old and editing a new contract
        '''
        self.assertEquals(ContractBase.query.count(), 2)

        # star and follow the contracts
        self.client.get('/scout/contracts/{}/subscribe'.format(self.contract1.id))
        self.client.get('/scout/contracts/{}/star'.format(self.contract1.id))

        # transition through the stages
        self.assign_contract()
        self.client.get(self.detail_view.format(self.contract1.id, self.stage1.id) + '?transition=true')
        self.client.get(self.detail_view.format(self.contract1.id, self.stage2.id) + '?transition=true')
        complete = self.client.get(self.detail_view.format(self.contract1.id, self.stage3.id) + '?transition=true')

        for stage in ContractStage.query.all():
            self.assertTrue(stage.entered is not None and stage.exited is not None)

        self.assertEquals(ContractBase.query.count(), 3)

        self.assertEquals(complete.status_code, 302)
        self.assertEquals(complete.location, 'http://localhost/conductor/contract/3/edit')

        # assert that the stars/follows were transferred over
        new_contract = ContractBase.query.get(3)
        # refresh our old contract, which has gone stale
        old_contract = ContractBase.query.get(1)

        self.assertEquals(len(new_contract.followers), 1)
        self.assertEquals(len(new_contract.starred), 1)
        self.assertEquals(len(old_contract.followers), 0)
        self.assertEquals(len(old_contract.starred), 0)

        # assert the parent/child relationship works
        self.assertEquals(new_contract.parent.id, old_contract.id)
        # assert our old contract is archived
        self.assertEquals(old_contract.is_archived, True)
        self.assertEquals(old_contract.description.lower(), self.contract1.description + ' [archived]')

    def test_edit_contract(self):
        '''Test edit metadata for contracts
        '''
        # subscribe to this contract
        self.login_user(self.conductor)
        self.client.get('/scout/contracts/1/subscribe')

        edit_contract_url = '/conductor/contract/{}/edit'.format(self.contract1.id)
        self.assert200(self.client.get(edit_contract_url))
        self.assert404(self.client.get('/conductor/contract/999/edit'))

        # test a form with malformed url
        bad_url = self.client.post(edit_contract_url, data={
            'contract_href': 'does not work!', 'description': 'this is a test',
            'expiration_date': datetime.date(2015, 9, 30),
            'financial_id': 1234, 'spec_number': 'test'
        }, follow_redirects=True)
        self.assertEquals(ContractBase.query.get(1).financial_id, self.contract1.financial_id)
        self.assert200(bad_url)
        self.assertTrue("That URL doesn&#39;t work!" in bad_url.data)

        # test a form with missing data
        missing_data = self.client.post(edit_contract_url, data={
            'contract_href': 'http://www.example.com', 'description': 'a different description!',
            'financial_id': 1234
        }, follow_redirects=True)
        self.assertEquals(ContractBase.query.get(1).financial_id, self.contract1.financial_id)
        self.assertEquals(ContractBase.query.get(1), self.contract1)
        self.assertTrue("This field is required." in missing_data.data)

        # test a good form
        with mail.record_messages() as outbox:
            good_post = self.client.post(edit_contract_url, data={
                'contract_href': 'http://www.example.com',
                'description': 'a different description!',
                'expiration_date': datetime.date(2015, 9, 30),
                'financial_id': 1234, 'spec_number': '1234'
            }, follow_redirects=True)
            self.assertEquals(ContractBase.query.get(1).contract_href, 'http://www.example.com')
            self.assertEquals(ContractBase.query.get(1).description, 'a different description!')
            self.assertEquals(len(outbox), 1)
            self.assertTrue('foo@foo.com' in outbox[0].send_to)
            self.assertTrue('[Pittsburgh Procurement] A contract you follow has been updated!' in outbox[0].subject)
            self.assertTrue('Successfully Updated' in good_post.data)

    @patch('urllib2.urlopen')
    def test_url_validation(self, urlopen):
        '''Test url validation HEAD requests work as expected
        '''
        mock_open = Mock()
        mock_open.getcode.side_effect = [200, urllib2.HTTPError('', 404, 'broken', {}, file)]
        urlopen.return_value = mock_open

        post_url = '/conductor/contract/{}/edit/url-exists'.format(self.contract1.id)

        post1 = self.client.post(
            post_url, data=json.dumps(dict(no_url='')),
            headers={'Content-Type': 'application/json;charset=UTF-8'}
        )
        self.assertEquals(json.loads(post1.data).get('status'), 404)

        post2 = self.client.post(
            post_url, data=json.dumps(dict(url='works')),
            headers={'Content-Type': 'application/json;charset=UTF-8'}
        )
        self.assertEquals(json.loads(post2.data).get('status'), 200)

        post3 = self.client.post(
            post_url, data=json.dumps(dict(url='doesnotwork')),
            headers={'Content-Type': 'application/json;charset=UTF-8'}
        )
        self.assertEquals(json.loads(post3.data).get('status'), 404)

    def test_conductor_contract_post_note(self):
        '''Test posting a note to the activity stream
        '''
        self.assign_contract()

        self.assertEquals(ContractStageActionItem.query.count(), 0)

        detail_view_url = self.build_detail_view(self.contract1)
        self.client.post(detail_view_url + '?form=activity', data=dict(
            note='a test note!'
        ))
        self.assertEquals(ContractStageActionItem.query.count(), 1)
        detail_view = self.client.get(detail_view_url)
        self.assertEquals(len(self.get_context_variable('actions')), 3)
        self.assertTrue('a test note!' in detail_view.data)

        # make sure you can't post notes to an unstarted stage
        self.assert404(self.client.post(
            self.build_detail_view(self.contract1, old_stage=self.stage3) + '?form=activity',
            data=dict(note='a test note!')
        ))

        # make sure you can't post a note to an unstarted contract
        self.assert404(self.client.post(
            self.build_detail_view(self.contract2) + '?form=activity',
            data=dict(note='a test note!')
        ))

    def test_delete_note(self):
        '''Test you can delete a note
        '''
        self.assign_contract()
        self.assertEquals(ContractStageActionItem.query.count(), 0)
        detail_view_url = self.build_detail_view(self.contract1)
        self.client.post(detail_view_url + '?form=activity', data=dict(
            note='a test note!'
        ))
        self.client.post(detail_view_url + '?form=activity', data=dict(
            note='a second test note!'
        ))

        self.assertEquals(ContractStageActionItem.query.count(), 2)
        self.client.get('/conductor/contract/1/stage/1/note/1/delete')
        self.assertEquals(ContractStageActionItem.query.count(), 1)

        self.client.get('/conductor/contract/1/stage/1/note/100/delete')
        self.assert_flashes("That note doesn't exist!", 'alert-warning')

        self.logout_user()
        # make sure you can't delete notes randomly
        self.assert200(
            self.client.get('/conductor/contract/1/stage/1/note/1/delete', follow_redirects=True)
        )
        self.assertEquals(ContractStageActionItem.query.count(), 1)
        self.assert_template_used('public/home.html')

    def test_conductor_send_update(self):
        '''Test sending an email/into the activity stream
        '''
        self.assign_contract()

        self.assertEquals(ContractStageActionItem.query.count(), 0)
        detail_view_url = self.build_detail_view(self.contract1)
        # make sure the form validators work
        bad_post = self.client.post(detail_view_url + '?form=update', data=dict(
            send_to='bademail', subject='test', body='test'
        ), follow_redirects=True)
        self.assertEquals(ContractStageActionItem.query.count(), 0)
        self.assertEquals(bad_post.status_code, 200)
        self.assertTrue('Invalid email address.' in bad_post.data)

        with mail.record_messages() as outbox:
            good_post = self.client.post(detail_view_url + '?form=update', data=dict(
                send_to='foo@foo.com', subject='test', body='test'
            ), follow_redirects=True)

            self.assertEquals(len(outbox), 1)
            self.assertEquals(ContractStageActionItem.query.count(), 1)
            self.assertTrue('foo@foo.com' in outbox[0].send_to)
            self.assertTrue('test' in outbox[0].subject)
            self.assertTrue('with the subject' in good_post.data)

    @unittest.skip('scout posting not supported yet')
    def test_conductor_post_to_scout(self):
        '''Test posting to scout from Conductor
        '''
        pass
