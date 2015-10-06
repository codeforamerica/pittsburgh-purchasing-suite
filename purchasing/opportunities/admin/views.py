# -*- coding: utf-8 -*-

import datetime

from flask import (
    render_template, url_for, Response, stream_with_context,
    redirect, flash, abort, request, current_app
)
from flask_login import current_user

from purchasing.database import db
from purchasing.extensions import login_manager
from purchasing.decorators import requires_roles
from purchasing.users.models import User

from purchasing.opportunities.models import Opportunity, Vendor, OpportunityDocument
from purchasing.opportunities.forms import OpportunityForm

from purchasing.notifications import Notification
from purchasing.opportunities.admin import blueprint

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

@blueprint.route('/opportunities/new', methods=['GET', 'POST'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def new():
    '''Create a new opportunity
    '''
    form = OpportunityForm()

    if form.validate_on_submit():
        opportunity_data = form.data_cleanup()
        opportunity = Opportunity.create(
            opportunity_data, current_user,
            form.documents, request.form.get('save_type') == 'publish'
        )
        db.session.add(opportunity)
        db.session.commit()

        opportunity.send_publish_email()
        db.session.commit()
        flash('Opportunity post submitted to OMB!', 'alert-success')
        return redirect(url_for('opportunities_admin.edit', opportunity_id=opportunity.id))

    form.display_cleanup()

    return render_template(
        'opportunities/admin/opportunity.html', form=form, opportunity=None,
        subcategories=form.get_subcategories(),
        categories=form.get_categories()
    )

@blueprint.route('/opportunities/<int:opportunity_id>', methods=['GET', 'POST'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def edit(opportunity_id):
    '''Edit an opportunity
    '''
    opportunity = Opportunity.query.get(opportunity_id)

    if opportunity:

        if opportunity.can_edit(current_user):
            form = OpportunityForm(obj=opportunity)

            if form.validate_on_submit():
                opportunity_data = form.data_cleanup()
                opportunity.update(
                    opportunity_data, current_user,
                    form.documents, request.form.get('save_type') == 'publish'
                )
                db.session.commit()
                opportunity.send_publish_email()
                db.session.commit()
                flash('Opportunity successfully updated!', 'alert-success')

                return redirect(url_for('opportunities_admin.edit', opportunity_id=opportunity.id))

            form.display_cleanup(opportunity)

            return render_template(
                'opportunities/admin/opportunity.html', form=form,
                opportunity=opportunity,
                subcategories=form.get_subcategories(),
                categories=form.get_categories()
            )

        flash('This opportunity has been locked for editing by OMB.', 'alert-warning')
        return redirect(url_for('opportunities.detail', opportunity_id=opportunity_id))
    abort(404)

@blueprint.route('/opportunities/<int:opportunity_id>/document/<int:document_id>/remove', methods=['GET', 'POST'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def remove_document(opportunity_id, document_id):
    try:
        document = OpportunityDocument.query.get(document_id)
        # TODO: delete the document from S3
        if document:
            current_app.logger.info(
                'BEACON DELETE DOCUMENT:\n Opportunity ID: {}\n Document: {}\n Location: {}'.format(
                    opportunity_id, document.name, document.href
                )
            )
            document.delete()
            flash('Document successfully deleted', 'alert-success')
        else:
            flash("That document doesn't exist!", 'alert-danger')
    except Exception, e:
        current_app.logger.error('Document delete error: {}'.format(str(e)))
        flash('Something went wrong: {}'.format(e.message), 'alert-danger')
    return redirect(url_for('opportunities_admin.edit', opportunity_id=opportunity_id))

@blueprint.route('/opportunities/<int:opportunity_id>/publish', methods=['GET'])
@requires_roles('admin', 'superadmin', 'conductor')
def publish(opportunity_id):
    '''Publish an opportunity
    '''
    opportunity = Opportunity.query.get(opportunity_id)
    if opportunity:
        opportunity.is_public = True
        db.session.commit()
        flash('Opportunity successfully published!', 'alert-success')

        Notification(
            to_email=[opportunity.created_by.email],
            subject='OMB approved your opportunity post!',
            html_template='opportunities/emails/staff_postapproved.html',
            txt_template='opportunities/emails/staff_postapproved.txt',
            opportunity=opportunity
        ).send(multi=True)

        current_app.logger.info(
'''BEACON APPROVED: ID: {} | Title: {} | Publish Date: {} | Submission Start Date: {} | Submission End Date: {} '''.format(
                opportunity.id, opportunity.description, str(opportunity.planned_publish),
                str(opportunity.planned_submission_start), str(opportunity.planned_submission_end)
            )
        )

        opportunity.send_publish_email()
        db.session.commit()

        return redirect(url_for('opportunities_admin.pending'))
    abort(404)

@blueprint.route('/opportunities/pending', methods=['GET'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def pending():
    '''View which contracts are currently pending approval
    '''
    pending = Opportunity.query.filter(
        Opportunity.is_public == False
    ).all()

    approved = Opportunity.query.filter(
        Opportunity.planned_publish > datetime.date.today(),
        Opportunity.is_public == True
    ).all()

    current_app.logger.info('BEACON PENDING VIEW')

    return render_template(
        'opportunities/admin/pending.html', pending=pending,
        approved=approved, current_user=current_user
    )

@blueprint.route('/signups')
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def signups():
    '''Basic dashboard view for category-level signups
    '''
    def stream():
        # yield the title columns
        yield 'first_name\tlast_name\tbusiness_name\temail\tphone_number\t' +\
            'minority_owned\twoman_owned\tveteran_owned\t' +\
            'disadvantaged_owned\tcategories\topportunities\n'

        vendors = Vendor.query.all()
        for vendor in vendors:
            row = vendor.build_downloadable_row()
            yield '\t'.join([str(i) for i in row]) + '\n'

    current_app.logger.info('BEACON VENDOR CSV DOWNLOAD')

    resp = Response(
        stream_with_context(stream()),
        headers={
            "Content-Disposition": "attachment; filename=vendors-{}.tsv".format(datetime.date.today())
        },
        mimetype='text/tsv'
    )

    return resp
