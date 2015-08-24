# -*- coding: utf-8 -*-

import os
import json

from collections import defaultdict

from flask import current_app

from flask_login import current_user
from werkzeug import secure_filename

from purchasing.utils import (
    connect_to_s3, _get_aggressive_cache_headers, random_id
)
from purchasing.database import db
from purchasing.opportunities.forms import OpportunityForm
from purchasing.opportunities.models import (
    Opportunity, RequiredBidDocument, Category, OpportunityDocument
)
from purchasing.users.models import User, Role

def get_categories(all_categories, form):
    '''Build category/subcategory lists/dictionaries
    '''
    categories, subcategories = set(), defaultdict(list)
    for category in all_categories:
        categories.add(category.category)
        subcategories['Select All'].append((category.id, category.category_friendly_name))
        subcategories[category.category].append((category.id, category.category_friendly_name))

    form.categories.choices = list(sorted(zip(categories, categories))) + [('Select All', 'Select All')]
    form.categories.choices.insert(0, ('', '-- Choose One --'))

    form.subcategories.choices = []

    return categories, subcategories, form

def fix_form_categories(request, form, cls, validate=None, obj=None,):
    '''Fix the incoming request form data to associate opps/vendors with categories

    Request - the flask request object
    form - the form whose data needs to be fixed
    cls - either Opportunity or Vendor, depending on the incoming context
    obj - the actual Opportunity or Vendor object
    validate - the field name to attach an errors to
    '''
    form_data = {c.name: form.data.get(c.name, None) for c in cls.__table__.columns if c.name not in ['id', 'created_at', 'created_by_id']}

    # manual fixup for opportunity-department relationship

    if form.data.get('department', None):
        form_data['department_id'] = form.data.get('department').id

    form_data['categories'] = obj.categories if obj else set()
    subcats = set()

    # manually iterate the form fields
    for k, v in request.form.iteritems():
        if not k.startswith('subcategories-'):
            continue
        else:
            subcat_id = int(k.split('-')[1])
            # make sure the field is checked (or 'on') and we don't have it already
            if v == 'on' and subcat_id not in subcats:
                subcats.add(subcat_id)
                subcat = Category.query.get(subcat_id)
                # make sure it's a valid category_friendly_name
                if subcat is None and validate:
                    form.errors[validate] = ['{} is not a valid choice!'.format(subcat)]
                    break
                form_data['categories'].add(subcat)

    if validate:
        if len(subcats) == 0 and not form.errors.get('subcategories', None):
            form.errors[validate] = ['You must choose at least one!']

    return form_data

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
        return _filename, filepath

def build_opportunity(data, publish=None, opportunity=None):
    '''Create/edit a new opportunity

    data - the form data from the request
    publish - either 'publish' or 'save':
      determines if the opportunity should be made public
    opportunity - the actual opportunity object
    '''
    contact_email = data.pop('contact_email')
    contact = User.query.filter(User.email == contact_email).first()

    # pop off our documents so they don't
    # get passed to the Opportunity constructor
    documents = data.pop('documents')

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

    for document in documents.entries:
        if document.title.data == '':
            continue

        _id = _id if _id else random_id(6)

        _file = document.document.data
        if _file.filename in [i.name for i in opp_documents]:
            continue

        filename, filepath = upload_document(_file, _id)
        if filepath:
            opportunity.opportunity_documents.append(OpportunityDocument(
                name=document.title.data, href=filepath
            ))

    if not opportunity.is_public:
        opportunity.is_public = True if publish == 'publish' else False

    db.session.commit()
    return opportunity

def generate_opportunity_form(obj=None, form=OpportunityForm):
    all_categories = Category.query.all()
    form = form(obj=obj)

    categories, subcategories, form = get_categories(all_categories, form)
    display_categories = subcategories.keys()
    if 'Select All' in display_categories:
        display_categories.remove('Select All')

    form.vendor_documents_needed.choices = [i.get_choices() for i in RequiredBidDocument.query.all()]

    return form, json.dumps(sorted(display_categories) + ['Select All']), json.dumps(subcategories)

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
