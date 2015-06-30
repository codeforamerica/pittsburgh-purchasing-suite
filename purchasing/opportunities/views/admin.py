# -*- coding: utf-8 -*-

import os

from flask import (
    render_template, url_for, current_app,
    redirect, flash, abort
)
from werkzeug import secure_filename

from purchasing.utils import (
    connect_to_s3, _get_aggressive_cache_headers, random_id
)
from purchasing.extensions import login_manager
from purchasing.decorators import requires_roles
from purchasing.opportunities.forms import OpportunityForm
from purchasing.opportunities.models import Opportunity, RequiredBidDocument
from purchasing.users.models import User
from purchasing.opportunities.views.blueprint import blueprint

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

def upload_document(document, _id=None):
    if document is None or document == '':
        return None, None

    filename = secure_filename(document.filename)
    _id = _id if _id else random_id(6)

    if filename == '':
        return None, None

    elif current_app.config.get('UPLOAD_S3') is True:
        # upload file to s3
        conn, bucket = connect_to_s3(
            current_app.config['AWS_ACCESS_KEY_ID'],
            current_app.config['AWS_SECRET_ACCESS_KEY'],
            current_app.config['UPLOAD_DESTINATION']
        )
        _document = bucket.new_key('opportunity-{}.pdf'.format(_id))
        aggressive_headers = _get_aggressive_cache_headers(_document)
        _document.set_contents_from_file(document, headers=aggressive_headers, replace=True)
        _document.set_acl('public-read')
        return _document.name, _document.generate_url(expires_in=0, query_auth=False)

    else:
        filepath = os.path.join(current_app.config['UPLOAD_DESTINATION'], filename)
        document.save(filepath)
        return filename, filepath

def build_opportunity(data, opportunity=None):
    contact_email = data.pop('contact_email')
    contact = User.query.filter(User.email == contact_email).first()

    if contact is None:
        contact = User().create(
            email=contact_email, role_id=2, department=data.get('department')
        )

    _id = opportunity.id if opportunity else None

    filename, filepath = upload_document(data.get('document', None), _id)

    data.update(dict(
        contact_id=contact.id, created_by=1,
        document=filename, document_href=filepath
    ))

    if opportunity:
        opportunity = opportunity.update(**data)
    else:
        opportunity = Opportunity.create(**data)
    return opportunity

@blueprint.route('/opportunities/admin/new', methods=['GET', 'POST'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def new():
    '''Create a new opportunity
    '''
    form = OpportunityForm()
    form.documents_needed.choices = [i.get_choices() for i in RequiredBidDocument.query.all()]
    if form.validate_on_submit():
        opportunity = build_opportunity(form.data)
        flash('Opportunity Successfully Created!', 'alert-success')
        return redirect(url_for('opportunities.edit', opportunity_id=opportunity.id))
    return render_template('opportunities/opportunity.html', form=form, opportunity=None)

@blueprint.route('/opportunities/<int:opportunity_id>/admin/edit', methods=['GET', 'POST'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def edit(opportunity_id):
    '''Edit an opportunity
    '''
    opportunity = Opportunity.query.get(opportunity_id)
    if opportunity:
        form = OpportunityForm(obj=opportunity)
        form.contact_email.data = opportunity.contact.email
        form.documents_needed.choices = [i.get_choices() for i in RequiredBidDocument.query.all()]
        if form.validate_on_submit():
            build_opportunity(form.data, opportunity=opportunity)
            flash('Opportunity Successfully Updated!', 'alert-success')
            return redirect(url_for('opportunities.edit', opportunity_id=opportunity.id))
        return render_template(
            'opportunities/opportunity.html', form=form, opportunity=opportunity
        )
    abort(404)
