# -*- coding: utf-8 -*-

import datetime

from flask import (
    render_template, url_for, Response, stream_with_context,
    redirect, flash, abort, request
)
from flask_login import current_user

from purchasing.database import db
from purchasing.extensions import login_manager
from purchasing.decorators import requires_roles
from purchasing.opportunities.models import (
    Opportunity, Category, Vendor, OpportunityDocument
)
from purchasing.users.models import (
    User, Role
)

from purchasing.opportunities.util import (
    fix_form_categories, generate_opportunity_form, build_opportunity,
    build_vendor_row
)

from purchasing.opportunities.admin import blueprint
from purchasing.notifications import Notification

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

@blueprint.route('/opportunities/new', methods=['GET', 'POST'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def new():
    '''Create a new opportunity
    '''
    form, categories, subcategories = generate_opportunity_form()

    if form.validate_on_submit():
        form_data = fix_form_categories(request, form, Opportunity, None)
        # add the contact email back on because it was stripped by the cleaning
        form_data['contact_email'] = form.data.get('contact_email')
        form_data['documents'] = form.documents
        # strip the is_public field from the form data, it's not part of the form
        form_data.pop('is_public')
        opportunity = build_opportunity(form_data, publish=request.form.get('save_type'))
        flash('Opportunity post submitted to OMB!', 'alert-success')

        Notification(
            to_email=[current_user.email],
            subject='Your post has been sent to OMB for approval',
            html_template='opportunities/emails/staff_postsubmitted.html',
            txt_template='opportunities/emails/staff_postsubmitted.txt',
            opportunity=opportunity
        ).send(multi=True)

        Notification(
            to_email=db.session.query(User.email).join(Role, User.role_id == Role.id).filter(
                Role.name.in_(['admin', 'superadmin'])
            ).all(),
            subject='A new Beacon post needs review',
            html_template='opportunities/emails/admin_postforapproval.html',
            txt_template='opportunities/emails/admin_postforapproval.txt',
            opportunity=opportunity
        ).send(multi=True)

        return redirect(url_for('opportunities_admin.edit', opportunity_id=opportunity.id))

    return render_template(
        'opportunities/admin/opportunity.html', form=form, opportunity=None,
        subcategories=subcategories,
        categories=categories
    )

@blueprint.route('/opportunities/<int:opportunity_id>', methods=['GET', 'POST'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def edit(opportunity_id):
    '''Edit an opportunity
    '''
    opportunity = Opportunity.query.get(opportunity_id)
    if opportunity:
        form, categories, subcategories = generate_opportunity_form(obj=opportunity)
        form.contact_email.data = opportunity.contact.email

        if form.validate_on_submit():
            form_data = fix_form_categories(request, form, Opportunity, opportunity)
            # add the contact email, documents back on because it was stripped by the cleaning
            form_data['contact_email'] = form.data.get('contact_email')
            form_data['documents'] = form.documents
            # strip the is_public field from the form data, it's not part of the form
            form_data.pop('is_public')
            build_opportunity(form_data, publish=request.form.get('save_type'), opportunity=opportunity)
            flash('Opportunity successfully updated!', 'alert-success')
            return redirect(url_for('opportunities_admin.edit', opportunity_id=opportunity.id))

        return render_template(
            'opportunities/admin/opportunity.html', form=form, opportunity=opportunity,
            subcategories=subcategories,
            categories=categories
        )
    abort(404)

@blueprint.route('/opportunities/<int:opportunity_id>/document/<int:document_id>/remove', methods=['GET', 'POST'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def remove_document(opportunity_id, document_id):
    try:
        document = OpportunityDocument.query.get(document_id)
        # TODO: delete the document from S3
        if document:
            document.delete()
            flash('Document successfully deleted', 'alert-success')
        else:
            flash("That document doesn't exist!", 'alert-danger')
    except Exception, e:
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

        if opportunity.is_published:
            opp_categories = [i.id for i in opportunity.categories]

            vendors = Vendor.query.filter(
                Vendor.categories.any(Category.id.in_(opp_categories))
            ).all()

            Notification(
                to_email=[i.email for i in vendors],
                subject='A new City of Pittsburgh opportunity from Beacon!',
                html_template='opportunities/emails/newopp.html',
                txt_template='opportunities/emails/newopp.txt',
                opportunity=opportunity
            ).send(multi=True)

            opportunity.publish_notification_sent = True

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
        Opportunity.planned_submission_start > datetime.date.today(),
        Opportunity.is_public == True
    ).all()

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
        yield 'first_name,last_name,business_name,email,phone_number,' +\
            'minority_owned,woman_owned,veteran_owned,' +\
            'disadvantaged_owned,categories,opportunities\n'

        vendors = Vendor.query.all()
        for vendor in vendors:
            row = build_vendor_row(vendor)
            yield ','.join([str(i) for i in row]) + '\n'

    resp = Response(
        stream_with_context(stream()),
        headers={
            "Content-Disposition": "attachment; filename=vendors-{}.csv".format(datetime.date.today())
        },
        mimetype='text/csv'
    )

    return resp
