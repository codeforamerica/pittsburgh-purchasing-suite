# -*- coding: utf-8 -*-

import datetime
import os
import json

from flask import (
    render_template, url_for, current_app, Response, stream_with_context,
    redirect, flash, abort, request, Blueprint
)
from flask_login import current_user
from werkzeug import secure_filename

from purchasing.utils import (
    connect_to_s3, _get_aggressive_cache_headers, random_id
)
from purchasing.database import db
from purchasing.extensions import login_manager
from purchasing.decorators import requires_roles
from purchasing.opportunities.forms import OpportunityForm
from purchasing.opportunities.models import (
    Opportunity, RequiredBidDocument, Category, Vendor, OpportunityDocument
)
from purchasing.users.models import User, Role
from purchasing.opportunities.util import get_categories, fix_form_categories
from purchasing.notifications import Notification

blueprint = Blueprint(
    'opportunities_admin', __name__, url_prefix='/beacon/admin',
    static_folder='../static', template_folder='../templates'
)

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

def upload_document(document, _id):
    if document is None or document == '':
        return None, None

    filename = secure_filename(document.filename)

    if filename == '':
        return None, None

    _filename = 'opportunity-{}-{}'.format(_id, filename)

    if current_app.config.get('UPLOAD_S3') is True:
        # upload file to s3
        conn, bucket = connect_to_s3(
            current_app.config['AWS_ACCESS_KEY_ID'],
            current_app.config['AWS_SECRET_ACCESS_KEY'],
            current_app.config['UPLOAD_DESTINATION']
        )
        _document = bucket.new_key(_filename)
        aggressive_headers = _get_aggressive_cache_headers(_document)
        _document.set_contents_from_file(document, headers=aggressive_headers, replace=True)
        _document.set_acl('public-read')
        return _document.name, _document.generate_url(expires_in=0, query_auth=False)

    else:
        try:
            os.mkdir(current_app.config['UPLOAD_DESTINATION'])
        except:
            pass

        filepath = os.path.join(current_app.config['UPLOAD_DESTINATION'], _filename)
        document.save(filepath)
        return filename, filepath

def build_opportunity(data, publish=None, opportunity=None):
    '''Create/edit a new opportunity

    data - the form data from the request
    publish - either 'publish' or 'save':
      determines if the opportunity should be made public
    opportunity - the actual opportunity object
    '''
    contact_email = data.pop('contact_email')
    contact = User.query.filter(User.email == contact_email).first()

    if contact is None:
        contact = User().create(
            email=contact_email,
            role=Role.query.filter(Role.name == 'staff').first(),
            department=data.get('department')
        )

    _id = opportunity.id if opportunity else None

    data.update(dict(contact_id=contact.id))

    if opportunity:
        opportunity = opportunity.update(**data)
    else:
        data.update(dict(created_by_id=current_user.id))
        opportunity = Opportunity.create(**data)

    opp_documents = opportunity.opportunity_documents.all()

    for _file in request.files.getlist('document'):

        _id = _id if _id else random_id(6)

        if _file.filename in [i.name for i in opp_documents]:
            continue

        filename, filepath = upload_document(_file, _id)

        if filename and filepath:
            opportunity.opportunity_documents.append(OpportunityDocument(
                name=filename, href=filepath
            ))

    if not opportunity.is_public:
        opportunity.is_public = True if publish == 'publish' else False

    db.session.commit()
    return opportunity

def generate_opportunity_form(obj=None):
    all_categories = Category.query.all()
    form = OpportunityForm(obj=obj)

    categories, subcategories, form = get_categories(all_categories, form)
    display_categories = subcategories.keys()
    display_categories.remove('Select All')

    form.vendor_documents_needed.choices = [i.get_choices() for i in RequiredBidDocument.query.all()]

    return form, json.dumps(sorted(display_categories) + ['Select All']), json.dumps(subcategories)

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
        opportunity = build_opportunity(form_data, publish=request.form.get('save_type'))
        flash('Opportunity Successfully Created!', 'alert-success')
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
            # add the contact email back on because it was stripped by the cleaning
            form_data['contact_email'] = form.data.get('contact_email')
            build_opportunity(form_data, publish=request.form.get('save_type'), opportunity=opportunity)
            flash('Opportunity Successfully Updated!', 'alert-success')
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

        return redirect(url_for('opportunities_admin.pending'))
    abort(404)

@blueprint.route('/opportunities/pending', methods=['GET'])
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def pending():
    '''View which contracts are currently pending approval
    '''
    opportunities = Opportunity.query.filter(
        Opportunity.is_public == False
    ).all()

    return render_template(
        'opportunities/admin/pending.html', opportunities=opportunities,
        current_user=current_user
    )

def build_downloadable_groups(val, iterable):
    '''Sorts and dedupes related lists

    Handles quoting, deduping, and sorting
    '''
    return '"' + '; '.join(
        sorted(list(set([i.__dict__[val] for i in iterable])))
    ) + '"'

def build_vendor_row(vendor):
    '''Takes in a vendor and returns a list of that vendor's properties

    Used to build the signup csv download
    '''
    return [
        vendor.first_name, vendor.last_name, vendor.business_name,
        vendor.email, vendor.phone_number, vendor.minority_owned,
        vendor.woman_owned, vendor.veteran_owned, vendor.disadvantaged_owned,
        build_downloadable_groups('category_friendly_name', vendor.categories),
        build_downloadable_groups('title', vendor.opportunities)
    ]

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
