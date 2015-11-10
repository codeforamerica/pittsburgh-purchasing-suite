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

    :status 200: Render the opportunity create/edit template
    :status 302: Post data for a new opportunity via the
        :py:class:`~purchasing.opportunities.forms.OpportunityForm`
        and redirect to the edit view of the created opportunity
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

    :status 200: Render the opportunity create/edit template
    :status 302: Post data for the relevant opportunity to edit via the
        :py:class:`~purchasing.opportunities.forms.OpportunityForm`
        and redirect to the edit view of the opportunity
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

@blueprint.route('/opportunities/<int:opportunity_id>/document/<int:document_id>/remove')
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def remove_document(opportunity_id, document_id):
    '''Remove a particular opportunity document

    .. seealso:
        :py:class:`~purchasing.opportunities.models.OpportunityForm`

    :status 302: Delete the relevant opportunity document and redirect to
        the edit view for the opportunity whose document was deleted
    '''
    try:
        document = OpportunityDocument.query.get(document_id)
        # TODO: delete the document from S3
        if document:
            current_app.logger.info(
'''BEACON DELETE DOCUMENT: | Opportunity ID: {} | Document: {} | Location: {}'''.format(
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

@blueprint.route('/opportunities/<int:opportunity_id>/publish')
@requires_roles('admin', 'superadmin', 'conductor')
def publish(opportunity_id):
    '''Publish an opportunity

    If an :py:class:`~purchasing.opportunities.models.Opportunity` has
    been created by a non-admin, it will be stuck in a "pending" state
    until it has been approved by an admin. This view function handles
    the publication event for a specific
    :py:class:`~purchasing.opportunities.models.Opportunity`

    :status 200: Publish the relevant opportunity and send the relevant
        publication emails
    :status 404: :py:class:`~purchasing.opportunities.models.Opportunity`
        not found
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
                opportunity.id, opportunity.title.encode('ascii', 'ignore'), str(opportunity.planned_publish),
                str(opportunity.planned_submission_start), str(opportunity.planned_submission_end)
            )
        )

        opportunity.send_publish_email()
        db.session.commit()

        return redirect(url_for('opportunities_admin.pending'))
    abort(404)

@blueprint.route('/opportunities/pending')
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def pending():
    '''View which contracts are currently pending approval

    :status 200: Render the pending template
    '''
    pending = Opportunity.query.filter(
        Opportunity.is_public == False,
        Opportunity.planned_submission_end >= datetime.date.today(),
        Opportunity.is_archived == False
    ).all()

    approved = Opportunity.query.filter(
        Opportunity.planned_publish > datetime.date.today(),
        Opportunity.is_public == True,
        Opportunity.planned_submission_end >= datetime.date.today(),
        Opportunity.is_archived == False
    ).all()

    current_app.logger.info('BEACON PENDING VIEW')

    return render_template(
        'opportunities/admin/pending.html', pending=pending,
        approved=approved, current_user=current_user
    )

@blueprint.route('/opportunities/<int:opportunity_id>/archive')
@requires_roles('admin', 'superadmin', 'conductor')
def archive(opportunity_id):
    '''Archives opportunities in pending view

    :status 302: Archive the :py:class:`~purchasing.opportunities.models.Opportunity`
        and redirect to the pending view
    :status 404: :py:class:`~purchasing.opportunities.models.Opportunity`
        not found
    '''
    opportunity = Opportunity.query.get(opportunity_id)
    if opportunity:
        opportunity.is_archived = True
        db.session.commit()

        current_app.logger.info(
'''BEACON ARCHIVED: ID: {} | Title: {} | Publish Date: {} | Submission Start Date: {} | Submission End Date: {} '''.format(
                opportunity.id, opportunity.title.encode('ascii', 'ignore'), str(opportunity.planned_publish),
                str(opportunity.planned_submission_start), str(opportunity.planned_submission_end)
            )
        )

        flash('Opportunity successfully archived!', 'alert-success')

        return redirect(url_for('opportunities_admin.pending'))

    abort(404)

@blueprint.route('/signups')
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def signups():
    '''Basic dashboard view for category-level signups

    :status 200: Download a tab-separated file of all vendor signups
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
