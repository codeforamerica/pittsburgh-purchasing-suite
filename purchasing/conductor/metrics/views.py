# -*- coding: utf-8 -*-

import datetime

from flask import render_template, stream_with_context, Response, abort, jsonify

from purchasing.database import db
from purchasing.decorators import requires_roles

from purchasing.data.flows import Flow
from purchasing.conductor.util import convert_to_str

from purchasing.conductor.metrics import blueprint

@blueprint.route('/')
@requires_roles('conductor', 'admin', 'superadmin')
def index():
    '''
    '''
    flows = Flow.query.all()
    return render_template('conductor/metrics/index.html', flows=flows)

@blueprint.route('/download/<int:flow_id>')
@requires_roles('conductor', 'admin', 'superadmin')
def download_tsv_flow(flow_id):
    '''
    '''
    flow = Flow.query.get(flow_id)
    if flow:

        tsv, headers = flow.reshape_metrics_granular()

        def stream():
            yield '\t'.join(headers) + '\n'
            for contract_id, values in tsv.iteritems():
                yield '\t'.join([str(i) for i in values]) + '\n'

        resp = Response(
            stream_with_context(stream()),
            headers={
                "Content-Disposition": "attachment; filename=conductor-{}-metrics.tsv".format(flow.flow_name)
            },
            mimetype='text/tsv'
        )

        return resp
    abort(404)

@blueprint.route('/download/all')
@requires_roles('conductor', 'admin', 'superadmin')
def download_all():
    '''Returns a tsv stream of all conductor contracts

    This works as a union of two large queries:
    * A query that gets all contracts that have no children
    * A query that gets all contracts which have parents

    Returns:
        A tsv follow with the following fields: the contract's id
        (item_number) contract's parent id (parent_item_number),
        the contract's description (description), the contract's
        expiration date (expiration_date) the contract parent's
        expiration date (parent_expiration), the department name
        (department), the assigned user's email address (assigned_to),
        the contract's spec number (spec_number), the contract
        parent's spec number (parent_spec), and a string with
        the status of a contract
    '''
    results = db.session.execute('''
    SELECT * FROM (
    SELECT
        c.id as item_number, null as parent_item_number,
        c.description, c.expiration_date, null as parent_expiration,
        d.name as department, u.email as assigned_to,
        cp.value as spec_number, null as parent_spec,
        CASE
            WHEN c.is_archived is True THEN 'archived'
            WHEN c.is_visible is False THEN 'removed from conductor'
            ELSE 'not started'
        END as status
    FROM contract c
    LEFT OUTER JOIN contract_property cp
    ON c.id = cp.contract_id
    LEFT OUTER JOIN users u
    ON c.assigned_to = u.id
    LEFT OUTER JOIN department d
    ON c.department_id = d.id
    LEFT OUTER JOIN contract_type ct
    ON c.contract_type_id = ct.id
    WHERE lower(ct.name) in ('county', 'a-bid', 'b-bid')
    AND lower(cp.key) = 'spec number'
    AND c.parent_id is null
    AND c.id not in (select parent_id from contract where parent_id is not null)

    UNION ALL

    SELECT
        c.id as item_number, p.id as parent_item_number,
        c.description, c.expiration_date, p.expiration_date as parent_expiration,
        d.name as department, u.email as assigned_to,
        cp.value as spec_number, pcp.value as parent_spec,
        CASE
            WHEN c.is_archived is True THEN 'archived'
            WHEN c.current_stage_id is null then 'not started'
            WHEN c.id in (select parent_id from contract where parent_id is not null) then 'completed'
            ELSE 'started'
        END as status
    FROM contract c
    INNER JOIN contract p
    ON c.parent_id = p.id
    LEFT OUTER JOIN contract_property cp
    ON c.id = cp.contract_id
    LEFT OUTER JOIN contract_property pcp
    ON c.parent_id = pcp.contract_id
    LEFT OUTER JOIN users u
    ON c.assigned_to = u.id
    LEFT OUTER JOIN department d
    ON c.department_id = d.id
    LEFT OUTER JOIN contract_type ct
    ON c.contract_type_id = ct.id
    WHERE lower(ct.name) in ('county', 'a-bid', 'b-bid')
    AND (lower(cp.key) = 'spec number' OR lower(pcp.key) = 'spec number')
    AND c.parent_id is not null

    ) x
    ORDER BY 1
    ''').fetchall()

    def stream():
        yield '\t'.join([str(i) for i in results[0].keys()]) + '\n'
        for row in results:
            yield '\t'.join([convert_to_str(i) for i in row]) + '\n'

    resp = Response(
        stream_with_context(stream()),
        headers={
            "Content-Disposition": "attachment; filename=conductor-all-{}.tsv".format(datetime.date.today())
        },
        mimetype='text/tsv'
    )

    return resp

@blueprint.route('/overview/<int:flow_id>')
@requires_roles('conductor', 'admin', 'superadmin')
def flow_overview(flow_id):
    flow = Flow.query.get(flow_id)
    if flow:
        return render_template('conductor/metrics/overview.html', flow=flow)
    abort(404)

@blueprint.route('/overview/<int:flow_id>/data')
@requires_roles('conductor', 'admin', 'superadmin')
def flow_data(flow_id):
    flow = Flow.query.get(flow_id)
    if flow:
        results = flow.build_metrics_data()
        return jsonify(
            {
                'complete': results['complete'].values(),
                'current': results['current'].values(),
                'stageDataObj': [{i.id: {'name': i.name, 'id': i.id}} for i in flow.build_detailed_stage_order()],
                'stageOrder': flow.stage_order
            }
        )
    abort(404)
