# -*- coding: utf-8 -*-

import datetime
from collections import defaultdict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from sqlalchemy.dialects.postgres import ARRAY

from purchasing.database import db, Model, Column
from purchasing.utils import localize_datetime
from purchasing.data.contracts import ContractBase
from purchasing.data.contract_stages import ContractStage, ContractStageActionItem
from purchasing.data.stages import Stage

class Flow(Model):
    __tablename__ = 'flow'

    id = Column(db.Integer, primary_key=True, index=True)
    flow_name = Column(db.Text, unique=True)
    contract = db.relationship('ContractBase', backref='flow', lazy='subquery')
    stage_order = Column(ARRAY(db.Integer))
    is_archived = Column(db.Boolean, default=False, nullable=False)

    def __unicode__(self):
        return self.flow_name

    @classmethod
    def all_flow_query_factory(cls):
        return cls.query

    def build_detailed_stage_order(self):
        return [Stage.query.get(i) for i in self.stage_order]

    def _build_row(self, row, exited, data_dict):
        try:
            data_dict[row.contract_id]['stages'].append({
                'name': row.stage_name, 'id': row.stage_id,
                'entered': localize_datetime(row.entered).isoformat(),
                'exited': localize_datetime(exited).isoformat(),
                'seconds': max([(exited - row.entered).total_seconds(), 0]),
            })
        except KeyError:
            data_dict[row.contract_id] = {
                'description': row.description,
                'email': row.email,
                'department': row.department,
                'contract_id': row.contract_id,
                'stages': [{
                    'name': row.stage_name, 'id': row.stage_id,
                    'entered': localize_datetime(row.entered).isoformat(),
                    'exited': localize_datetime(exited).isoformat(),
                    'seconds': max([(exited - row.entered).total_seconds(), 0]),
                }]
            }

        return data_dict

    def build_metrics_data(self):
        raw_data = self.get_metrics_csv_data()
        results = {'current': {}, 'complete': {}}

        for ix, row in enumerate(raw_data):
            exited = row.exited if row.exited else datetime.datetime.utcnow()
            if row.exited is None:
                results['current'] = self._build_row(row, exited, results['current'])
            else:
                results['complete'] = self._build_row(row, exited, results['complete'])

        return results

    def reshape_metrics_granular(self, enter_and_exit=False, flat=True):
        '''Transform long data from database into wide data for consumption

        Take in a result set (list of tuples), return a dictionary of results.
        The key for the dictionary is the contract id, and the values are a list
        of (fieldname, value). Metadata (common to all rows) is listed first, and
        timing information from each stage is listed afterwords. Sorting is assumed
        to be done on the database layer
        '''
        raw_data = self.get_metrics_csv_data()
        results = defaultdict(list)
        headers = []

        for ix, row in enumerate(raw_data):
            if ix == 0:
                headers.extend(['item_number', 'description', 'assigned_to', 'department'])

            # if this is a new contract row, append metadata
            if len(results[row.contract_id]) == 0:
                results[row.contract_id].extend([
                    row.contract_id,
                    row.description,
                    row.email,
                    row.department,
                ])

            # append the stage date data
            if enter_and_exit and row.exited:
                results[row.contract_id].extend([
                    localize_datetime(row.exited),
                    localize_datetime(row.entered)
                ])
                if row.stage_name + '_exit' not in headers:
                    headers.append(row.stage_name.replace(' ', '_') + '_exit')
                    headers.append(row.stage_name.replace(' ', '_') + '_enter')
            else:
                results[row.contract_id].extend([
                    localize_datetime(row.exited)
                ])

                if row.stage_name not in headers:
                    headers.append(row.stage_name)

        return results, headers

    def get_metrics_csv_data(self):
        return db.session.execute('''
            select
                x.contract_id, x.description, x.department,
                x.email, x.stage_name, x.rn, x.stage_id,
                min(x.entered) as entered,
                max(x.exited) as exited

            from (

                select
                    c.id as contract_id, c.description, d.name as department,
                    u.email, s.name as stage_name, s.id as stage_id, cs.exited, cs.entered,
                    row_number() over (partition by c.id order by cs.entered asc, cs.id asc) as rn

                from contract_stage cs
                join stage s on cs.stage_id = s.id

                join contract c on cs.contract_id = c.id

                join users u on c.assigned_to = u.id
                left join department d on c.department_id = d.id

                where cs.entered is not null
                and cs.flow_id = :flow_id

            ) x
            group by 1,2,3,4,5,6,7
            order by contract_id, rn asc
        ''', {
            'flow_id': self.id
        }).fetchall()

def create_contract_stages(flow_id, contract_id, contract=None):
    '''Creates new rows in contract_stage table.

    Extracts the rows out of the given flow, and creates new rows
    in the contract_stage table for each of them.
    '''
    revert = False
    contract = contract if contract else ContractBase.query.get(contract_id)
    stages = Flow.query.get(flow_id).stage_order
    contract_stages = []
    for stage_id in stages:
        try:
            contract_stages.append(ContractStage.create(
                contract_id=contract_id,
                flow_id=flow_id,
                stage_id=stage_id,
            ))

        except (IntegrityError, FlushError):
            revert = True
            db.session.rollback()
            stage = ContractStage.query.filter(
                ContractStage.contract_id == contract_id,
                ContractStage.flow_id == flow_id,
                ContractStage.stage_id == stage_id
            ).first()
            if stage:
                contract_stages.append(stage)
            else:
                raise IntegrityError

        except Exception:
            raise

    contract.flow_id = flow_id
    db.session.commit()

    return stages, contract_stages, revert

def switch_flow(new_flow_id, contract_id, user):
    '''Switch the contract's progress from one flow to another

    Instead of trying to do anything too smart, we prefer instead
    to be dumb -- it is better to force the user to click ahead
    through a bunch of stages than it is to incorrectly fast-forward
    them to an incorrect state.

    There are five concrete actions here:
        1. Fully revert all stages in the old flow
        2. Rebuild our flow/stage model for the new order.
        3. Attach the complete log of the old flow into the first stage
          of the new order.
        4. Strip the contract's current stage id.
        5. Transition into the first stage of the new order. This will
          ensure that everything is being logged in the correct order.
    '''
    # get our contract and its complete action history
    contract = ContractBase.query.get(contract_id)
    old_flow = contract.flow.flow_name
    old_action_log = contract.filter_action_log()

    # fully revert all used stages in the old flow
    for contract_stage in ContractStage.query.filter(
        ContractStage.contract_id == contract_id,
        ContractStage.flow_id == contract.flow_id,
        ContractStage.entered != None
    ).all():
        contract_stage.full_revert()
        contract_stage.strip_actions()

    db.session.commit()

    # create the new stages
    new_stages, new_contract_stages, revert = create_contract_stages(
        new_flow_id, contract_id, contract=contract
    )

    # log that we are switching flows into the first stage
    switch_log = ContractStageActionItem(
        contract_stage_id=new_contract_stages[0].id, action_type='flow_switch',
        taken_by=user.id, taken_at=datetime.datetime.utcnow(),
        action_detail={
            'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
            'date': datetime.datetime.utcnow().strftime('%Y-%m-%d'),
            'type': 'flow_switched', 'old_flow': old_flow,
            'new_flow': contract.flow.flow_name,
            'old_flow_actions': [i.as_dict() for i in old_action_log]
        }
    )
    db.session.add(switch_log)
    db.session.commit()

    # remove the current_stage_id from the contract
    # so we can start the new flow
    contract.current_stage_id = None
    contract.flow_id = new_flow_id

    destination = None
    if revert:
        destination = new_stages[0]

    # transition into the first stage of the new flow
    actions = contract.transition(user, destination=destination)
    for i in actions:
        db.session.add(i)

    db.session.commit()
    return new_contract_stages[0], contract
