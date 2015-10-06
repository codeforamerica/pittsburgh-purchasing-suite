# -*- coding: utf-8 -*-

import os
import re
import datetime
import json
import pytz

from collections import defaultdict

from werkzeug import secure_filename

from flask import current_app, request
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed
from wtforms import widgets, fields, Form as NoCSRFForm
from wtforms.ext.dateutil.fields import DateTimeField
from wtforms.validators import (
    DataRequired, Email, ValidationError, Optional
)
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

from purchasing.opportunities.models import Vendor, Category, RequiredBidDocument

from purchasing.utils import RequiredIf
from purchasing.users.models import User, Department
from purchasing.data.contracts import ContractType
from purchasing.opportunities.util import parse_contact

from purchasing.utils import connect_to_s3, _get_aggressive_cache_headers

ALL_INTEGERS = re.compile('[^\d.]')
DOMAINS = re.compile('@[\w.]+')

def build_label_tooltip(name, description, href):
    return '''
    {} <i
        class="fa fa-question-circle"
        aria-hidden="true" data-toggle="tooltip"
        data-placement="right" title="{}">
    </i>'''.format(name, description)

def select_multi_checkbox(field, ul_class='', **kwargs):
    '''Custom multi-select widget for vendor documents needed

    Renders with tooltips describing each document
    '''
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<div %s>' % widgets.html_params(id=field_id, class_=ul_class)]
    for value, label, _ in field.iter_choices():
        name, description, href = label
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if int(value) in field.data:
            options['checked'] = 'checked'
        html.append(u'<div class="checkbox">')
        html.append(u'<input %s /> ' % widgets.html_params(**options))
        html.append(u'<label for="%s">%s</label>' % (choice_id, build_label_tooltip(name, description, href)))
        html.append(u'</div>')
    html.append(u'</div>')
    return u''.join(html)

def email_present(form, field):
    '''Checks that we have a vendor with that email address
    '''
    if field.data:
        vendor = Vendor.query.filter(Vendor.email == field.data).first()
        if vendor is None:
            raise ValidationError("We can't find the email {}!".format(field.data))

def city_domain_email(form, field):
    '''Checks that the email is a current user or a city domain
    '''
    if field.data:
        user = User.query.filter(User.email == field.data).first()
        if user is None:
            domain = re.search(DOMAINS, field.data)
            if domain and domain.group().lstrip('@') != current_app.config.get('CITY_DOMAIN'):
                raise ValidationError("That's not a valid contact!")

def max_words(max=500):
    message = 'Text cannot be more than {} words! You had {} words.'

    def _max_words(form, field):
        l = field.data and len(field.data.split()) or 0
        if l > max:
            raise ValidationError(message.format(max, l))

    return _max_words

def after_today(form, field):
    if isinstance(field.data, datetime.datetime):
        to_test = field.data.date()
    elif isinstance(field.data, datetime.date):
        to_test = field.data
    else:
        raise ValidationError('This must be a date')

    if to_test <= datetime.date.today():
        raise ValidationError('The deadline has to be after today!')

class MultiCheckboxField(fields.SelectMultipleField):
    '''Custom multiple select that displays a list of checkboxes

    We have a custom pre_validate to handle cases where a
    user has choices from multiple categories. This will insert
    those selected choices into the CHOICES on the class, allowing
    the validation to pass.
    '''
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

    def pre_validate(self, form):
        pass

class DynamicSelectField(fields.SelectField):
    def pre_validate(self, form):
        if len(self.data) == 0:
            raise ValidationError('You must select at least one!')
            return False
        for category in self.data:
            if isinstance(category, Category):
                self.choices.append([category, category])
                continue
            else:
                raise ValidationError('Invalid category!')
                return False
        return True

def validate_phone_number(form, field):
    '''Strips out non-integer characters, checks that it is 10-digits
    '''
    if field.data:
        value = re.sub(ALL_INTEGERS, '', field.data)
        if len(value) != 10 and len(value) != 0:
            raise ValidationError('Invalid 10-digit phone number!')

class CategoryForm(Form):
    subcategories = MultiCheckboxField(coerce=int, choices=[])
    categories = DynamicSelectField(choices=[])

    def get_categories(self):
        return self._categories

    def get_subcategories(self):
        return self._subcategories

    def pop_categories(self, categories=True, subcategories=True):
        cleaned_data = self.data
        cleaned_data.pop('categories') if categories else None
        cleaned_data.pop('subcategories') if subcategories else None
        return cleaned_data

    def build_categories(self, all_categories):
        '''Build category/subcategory lists/dictionaries
        '''
        categories, subcategories = set(), defaultdict(list)
        for category in all_categories:
            categories.add(category.category)
            subcategories['Select All'].append((category.id, '{} - {}'.format(category.category_friendly_name, category.category)))
            subcategories[category.category].append((category.id, category.category_friendly_name))

        self.categories.choices = list(sorted(zip(categories, categories))) + [('Select All', 'Select All')]
        self.categories.choices.insert(0, ('', '-- Choose One --'))

        self.subcategories.choices = []
        return subcategories

    def display_cleanup(self, all_categories=None):
        all_categories = all_categories if all_categories else Category.query.all()
        subcategories = self.build_categories(all_categories)
        self._subcategories = json.dumps(subcategories)
        display_categories = subcategories.keys()

        if 'Select All' in display_categories:
            display_categories.remove('Select All')
        self._categories = json.dumps(sorted(display_categories))

    def process(self, formdata=None, obj=None, data=None, **kwargs):
        super(CategoryForm, self).process(formdata, obj, data, **kwargs)

        self.categories.data = obj.categories if obj and hasattr(obj, 'categories') else set()
        subcats = set()

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
                    if subcat is None:
                        self.errors['subcategories'] = ['{} is not a valid choice!'.format(subcat)]
                        break
                    self.categories.data.add(subcat)

class VendorSignupForm(CategoryForm):
    business_name = fields.TextField(validators=[DataRequired()])
    email = fields.TextField(validators=[DataRequired(), Email()])
    first_name = fields.TextField()
    last_name = fields.TextField()
    phone_number = fields.TextField(validators=[validate_phone_number])
    fax_number = fields.TextField(validators=[validate_phone_number])
    woman_owned = fields.BooleanField('Woman-owned business')
    minority_owned = fields.BooleanField('Minority-owned business')
    veteran_owned = fields.BooleanField('Veteran-owned business')
    disadvantaged_owned = fields.BooleanField('Disadvantaged business enterprise')
    subscribed_to_newsletter = fields.BooleanField(
        label='Biweekly update on all opportunities posted to Beacon', validators=[Optional()],
        default="checked"
    )

class OpportunitySignupForm(Form):
    business_name = fields.TextField(validators=[DataRequired()])
    email = fields.TextField(validators=[DataRequired(), Email()])
    also_categories = fields.BooleanField()

class UnsubscribeForm(Form):
    email = fields.TextField(validators=[DataRequired(), Email(), email_present])
    categories = MultiCheckboxField(coerce=int)
    opportunities = MultiCheckboxField(coerce=int)
    subscribed_to_newsletter = fields.BooleanField(
        label='Biweekly update on all opportunities posted to Beacon', validators=[Optional()],
        default='checked'
    )

class OpportunityDocumentForm(NoCSRFForm):
    title = fields.TextField(label='Document Name', validators=[RequiredIf('document')])
    document = FileField('Document', validators=[FileAllowed(
        ['pdf', 'doc', 'docx', 'xls', 'xlsx'],
        '.pdf, Word (.doc/.docx), and Excel (.xls/.xlsx) documents only!'),
        RequiredIf('title')]
    )

    def upload_document(self, _id):
        if self.document.data is None or self.document.data == '':
            return None, None

        filename = secure_filename(self.document.data.filename)

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
            _document.set_contents_from_file(self.document.data, headers=aggressive_headers, replace=True)
            _document.set_acl('public-read')
            return _document.name, _document.generate_url(expires_in=0, query_auth=False)

        else:
            try:
                os.mkdir(current_app.config['UPLOAD_DESTINATION'])
            except:
                pass

            filepath = os.path.join(current_app.config['UPLOAD_DESTINATION'], _filename)
            self.document.data.save(filepath)
            return _filename, filepath

class OpportunityForm(CategoryForm):
    department = QuerySelectField(
        query_factory=Department.query_factory,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='-----',
        validators=[DataRequired()]
    )
    opportunity_type = QuerySelectField(
        query_factory=ContractType.opportunity_type_query,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='-----',
        validators=[DataRequired()]
    )
    contact_email = fields.TextField(validators=[Email(), city_domain_email, DataRequired()])
    title = fields.TextField(validators=[DataRequired()])
    description = fields.TextAreaField(validators=[max_words(), DataRequired()])
    planned_publish = fields.DateField(validators=[DataRequired()])
    planned_submission_start = fields.DateField(validators=[DataRequired()])
    planned_submission_end = DateTimeField(validators=[after_today, DataRequired()])
    vendor_documents_needed = QuerySelectMultipleField(
        widget=select_multi_checkbox,
        query_factory=RequiredBidDocument.query_factory,
        get_pk=lambda i: i[0],
        get_label=lambda i: i[1]
    )
    documents = fields.FieldList(fields.FormField(OpportunityDocumentForm), min_entries=1)

    def display_cleanup(self, opportunity=None):
        self.vendor_documents_needed.choices = [i.get_choices() for i in RequiredBidDocument.query.all()]
        if opportunity and not self.contact_email.data:
            self.contact_email.data = opportunity.contact.email

        if self.planned_submission_end.data:
            self.planned_submission_end.data = pytz.UTC.localize(
                self.planned_submission_end.data
            ).astimezone(current_app.config['DISPLAY_TIMEZONE'])

        super(OpportunityForm, self).display_cleanup()

    def data_cleanup(self):
        opportunity_data = self.pop_categories(categories=False)
        opportunity_data.pop('documents')

        opportunity_data['department_id'] = self.department.data.id
        opportunity_data['contact_id'] = parse_contact(opportunity_data.pop('contact_email'), self.department.data)
        opportunity_data['vendor_documents_needed'] = [int(i[0]) for i in opportunity_data['vendor_documents_needed']]
        return opportunity_data

    def process(self, formdata=None, obj=None, data=None, **kwargs):
        super(OpportunityForm, self).process(formdata, obj, data, **kwargs)
        if self.planned_submission_end.data and formdata:
            self.planned_submission_end.data = current_app.config['DISPLAY_TIMEZONE'].localize(
                self.planned_submission_end.data
            ).astimezone(pytz.UTC).replace(tzinfo=None)
