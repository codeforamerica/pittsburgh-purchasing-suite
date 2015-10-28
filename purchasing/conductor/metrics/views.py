# -*- coding: utf-8 -*-

from flask import render_template, stream_with_context, Response, abort, jsonify

from purchasing.decorators import requires_roles

from purchasing.data.flows import Flow
from purchasing.data.stages import Stage

from purchasing.conductor.metrics import blueprint

@blueprint.route('/')
@requires_roles('conductor', 'admin', 'superadmin')
def index():
    flows = Flow.query.all()
    return render_template('conductor/metrics/index.html', flows=flows)

@blueprint.route('/download/<int:flow_id>')
@requires_roles('conductor', 'admin', 'superadmin')
def download_tsv_flow(flow_id):
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

