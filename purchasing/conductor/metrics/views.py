# -*- coding: utf-8 -*-

from flask import render_template, stream_with_context, Response

from purchasing.database import db
from purchasing.decorators import requires_roles

from purchasing.data.models import Flow
from purchasing.conductor.util import reshape_metrics_granular

from purchasing.conductor.metrics import blueprint

@blueprint.route('/')
@requires_roles('conductor', 'admin', 'superadmin')
def index():
    return render_template('conductor/metrics/index.html')

@blueprint.route('/download/<int:flow_id>')
@requires_roles('conductor', 'admin', 'superadmin')
def download_csv_flow(flow_id):
    flow = Flow.query.get(flow_id)

    stages = db.session.execute(
        '''
        select
            x.contract_id, x.description, x.department,
            x.email, x.stage_name, x.exited, x.rn

        from (

            select
                c.id as contract_id, c.description, d.name as department,
                u.email, s.name as stage_name, cs.exited,
                row_number() over (partition by c.id order by cs.id asc) as rn

            from contract_stage cs
            join stage s on cs.stage_id = s.id

            join contract c on cs.contract_id = c.id

            join users u on c.assigned_to = u.id
            left join department d on c.department_id = d.id

            where cs.entered is not null
            and cs.exited is not null
            and cs.flow_id = :flow_id

        ) x
        order by contract_id, rn desc
        ''',
        {
            'flow_id': flow_id
        }
    ).fetchall()

    csv, headers = reshape_metrics_granular(stages)

    def stream():
        yield ','.join(headers) + '\n'
        for contract_id, values in csv.iteritems():
            yield ','.join([str(i) for i in values]) + '\n'

    resp = Response(
        stream_with_context(stream()),
        headers={
            "Content-Disposition": "attachment; filename=conductor-{}-metrics.csv".format(flow.flow_name)
        },
        mimetype='text/csv'
    )

    return resp
