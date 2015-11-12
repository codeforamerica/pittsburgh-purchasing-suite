# -*- coding: utf-8 -*-

import datetime
from collections import defaultdict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from sqlalchemy.dialects.postgres import ARRAY

from purchasing.database import db, Model, Column
from purchasing.utils import localize_datetime
from purchasing.data.contract_stages import ContractStage
from purchasing.data.stages import Stage

class Flow(Model):
    '''Model for flows

    A Flow is the series of :py:class:`~purchasing.data.stages.Stage` objects
    that a contract will go through as part of Conductor. It is meant to be
    as configurable and flexible as possible. Because of the nature of Flows,
    it is best to not allow them to be edited or deleted once they are in use.
    Instead, there is an ``is_archived`` flag. This is because of the difficulty
    of knowing how to handle contracts that are currently in the middle of a flow
    if that flow is edited. Instead, it is better to create a new flow.

    Attributes:
        id: Primary key unique ID
        flow_name: Name of this flow
        contract: Many-to-one relationship with
            :py:class:`~purchasing.data.contracts.ContractBase` (many
            contracts can share a flow)
        stage_order: Array of stage_id integers
        is_archived: Boolean of whether the flow is archived or active
    '''
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
        '''Query factory that returns query of all flows
        '''
        return cls.query

    @classmethod
    def nonarchived_query_factory(cls):
        '''Query factory that returns query of all non-archived flows
        '''
        return cls.query.filter(cls.is_archived == False)

    def get_ordered_stages(self):
        '''Turns the flow's stage_order attribute into Stage objects

        Returns:
            Ordered list of :py:class:`~purchasing.data.stages.Stage` objects
            in the flow's ``stage_order``
        '''
        return [Stage.query.get(i) for i in self.stage_order]

    def create_contract_stages(self, contract):
        '''Creates new rows in contract_stage table.

        Extracts the rows out of the given flow, and creates new rows
        in the contract_stage table for each of them.

        If the stages already exist, that means that the contract
        is switching back into a flow that it had already been in.
        To handle this, the "revert" flag is set to true, which
        should signal to a downstream process to roll the stages
        back to the first one in the current flow.

        Arguments:
            contract: A :py:class:`~purchasing.data.contracts.ContractBase` object

        Returns:
            A three-tuple of (the flow's stage order, a list of the flow's
            :py:class:`~purchasing.data.contract_stages.ContractStage` objects,
            whether the we are "reverting")

        '''
        revert = False
        contract_stages = []
        for stage_id in self.stage_order:
            try:
                contract_stages.append(ContractStage.create(
                    contract_id=contract.id,
                    flow_id=self.id,
                    stage_id=stage_id,
                ))
            except (IntegrityError, FlushError):
                revert = True
                db.session.rollback()
                stage = ContractStage.query.filter(
                    ContractStage.contract_id == contract.id,
                    ContractStage.flow_id == self.id,
                    ContractStage.stage_id == stage_id
                ).first()
                if stage:
                    contract_stages.append(stage)
                else:
                    raise IntegrityError

            except Exception:
                raise

        contract.flow_id = self.id
        db.session.commit()

        return self.stage_order, contract_stages, revert

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
        '''Build the raw data sets to be transformed client-side for metrics charts

        Example:
            .. code-block:: python

                results = {
                    'current': { 'contract id': {
                        'description': 'a contract description',
                        'email': 'the contract is assigned to this email',
                        'department': 'the primary department for the contract',
                        'contract_id': 'the contract id',
                        'stages': [{
                            'name': 'the stage name', 'id': 'the stage id',
                            'entered': 'when the stage was entered',
                            'exited': 'when the stage was exited',
                            'seconds': 'number of seconds the contract spent in this stage',
                        }, ...]
                    }, ... },
                    'complete': { 'contract id': {

                    }, ... }
                }

        Returns:
            A results dictionary described in the example above.
        '''
        raw_data = self.get_metrics_csv_data()
        results = {'current': {}, 'complete': {}}

        for ix, row in enumerate(raw_data):
            exited = row.exited if row.exited else datetime.datetime.utcnow()
            if row.exited is None:
                results['current'] = self._build_row(row, exited, results['current'])
            else:
                results['complete'] = self._build_row(row, exited, results['complete'])

        return results

    def reshape_metrics_granular(self, enter_and_exit=False):
        '''Transform long data from database into wide data for consumption

        Take in a result set (list of tuples), return a dictionary of results.
        The key for the dictionary is the contract id, and the values are a list
        of (fieldname, value). Metadata (common to all rows) is listed first, and
        timing information from each stage is listed afterwords. Sorting is assumed
        to be done on the database layer

        Arguments:
            enter_and_exit: A boolean option of whether to add both the
                enter and exit times to the results list

        Returns:
            * Results - a dictionary of lists which can be used to generate
              a .csv or .tsv file to be downloaded by the client
            * Headers - A list of strings which can be used to create the
              headers for the downloadable file
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
        '''Raw SQL query that returns the raw data to be reshaped for download or charting
        '''
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
