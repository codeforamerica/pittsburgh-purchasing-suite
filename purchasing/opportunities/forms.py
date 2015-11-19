# -*- coding: utf-8 -*-

import os
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

from purchasing.opportunities.models import Category, RequiredBidDocument

from purchasing.utils import RequiredIf
from purchasing.users.models import Department
from purchasing.data.contracts import ContractType
from purchasing.opportunities.util import parse_contact, select_multi_checkbox
from purchasing.opportunities.validators import (
    email_present, city_domain_email, max_words,
    after_now, validate_phone_number
)

from purchasing.utils import connect_to_s3, _get_aggressive_cache_headers

class MultiCheckboxField(fields.SelectMultipleField):
    '''Custom multiple select field that displays a list of checkboxes

    We have a custom ``pre_validate`` to handle cases where a
    user has choices from multiple categories.
    the validation to pass.

    Attributes:
        widget: wtforms
            `ListWidget <http://wtforms.readthedocs.org/en/latest/widgets.html#wtforms.widgets.ListWidget>`_
        option_widget: wtforms
            `CheckboxInput <http://wtforms.readthedocs.org/en/latest/widgets.html#wtforms.widgets.CheckboxInput>`_
    '''
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

    def pre_validate(self, form):
        '''Automatically passes

        We override pre-validate to allow the form to use
        dynamically created CHOICES.

        See Also:
            :py:class:`~purchasing.opportunities.models.Category`,
            :py:class:`~purchasing.opportunities.forms.CategoryForm`
        '''
        pass

class DynamicSelectField(fields.SelectField):
    '''Custom dynamic select field
    '''
    def pre_validate(self, form):
        '''Ensure we have at least one Category and they all correctly typed

        See Also:
            * :py:class:`~purchasing.opportunities.models.Category`
        '''
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

class CategoryForm(Form):
    '''Base form for anything involving Beacon categories

    "Categories" and "Subcategories" are originally derived from NIGP codes.
    NIGP codes can be somewhat hard to parse and aren't updated incredibly
    regularly, especially when it comes to things like IT services and software.
    Therefore, we took time to devise our own descriptions of things that map back
    to NIGP codes. The category form is the UI representation of that mapping. Each
    detailed "subcategory" has a parent "category" to which it belongs. Users
    select the "parent" category they are interested in, and a series of checkboxes
    are presented to them. This raises some interesting challenges for validation,
    which are handled in the ``process`` method.

    See Also:
        * :py:func:`~purchasing.opportunities.util.select_multi_checkbox`
            widget used to generate the UI components through jinja templates.

        * :py:class:`~purchasing.opportunities.models.Category`
            base object that is used to build the CategoryForm.

    Attributes:
        subcategories: A :py:class:`~purchasing.opportunities.forms.MultiCheckboxField`
        categories: A :py:class:`~purchasing.opportunities.forms.DynamicSelectField`
    '''

    subcategories = MultiCheckboxField(coerce=int, choices=[])
    categories = DynamicSelectField(choices=[])

    def get_categories(self):
        '''Getter for the form's parent categories
        '''
        return self._categories

    def get_subcategories(self):
        '''Getter for the form's subcategories
        '''
        return self._subcategories

    def pop_categories(self, categories=True, subcategories=True):
        '''Pop categories and/or subcategories off of the Form's ``data`` attribute

        In order to prevent wtforms from throwing ValidationErrors improperly, we
        need to modify some of the internal form data. This method allows us to pop
        off the categories or subcategories of the form data as necessary.

        Arguments:
            categories: Pop categories from form's data if True
            subcategories: Pop subcategories from form's data if True

        Returns:
            Modified form data with categories and/or subcategories removed as necessary
        '''
        cleaned_data = self.data
        cleaned_data.pop('categories') if categories else None
        cleaned_data.pop('subcategories') if subcategories else None
        return cleaned_data

    def build_categories(self, all_categories):
        '''Build form's category and subcategory choices

        For our :py:func:`~purchasing.opportunities.util.select_multi_checkbox`, we need to give
        both top-level choices for the select field and individual level subcategories.
        This method creates those and modifies the form in-place to build the appropriate choices

        Arguments:
            all_categories: A list of :py:class:`~purchasing.opportunities.models.Category` objects

        Returns:
            A dictionary with top-level parent category names as keys and
                list of that parent's subcategories as values.
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
        '''Clean up form's data for display purposes:

        1. Constructs and modifies the form's ``categories`` and ``subcategories``
        2. Creates the template-used subcatgories and display categories
        3. Removed the ``Select All`` choice from the available categories

        Arguments:
            all_categories: A list of :py:class:`~purchasing.opportunities.models.Category` objects,
            or None. If None, defaults to all Categories.
        '''
        all_categories = all_categories if all_categories else Category.query.all()
        subcategories = self.build_categories(all_categories)
        self._subcategories = json.dumps(subcategories)
        display_categories = subcategories.keys()

        if 'Select All' in display_categories:
            display_categories.remove('Select All')
        self._categories = json.dumps(sorted(display_categories))

    def process(self, formdata=None, obj=None, data=None, **kwargs):
        '''Process the form and append data to the ``categories``

        Manually iterates through the flask Request.form, appending valid
        Categories to the form's ``categories`` data

        See Also:
            For more information about parameters, see the `Wtforms base form
            <http://wtforms.readthedocs.org/en/latest/forms.html#wtforms.form.BaseForm.process>`_
        '''
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
    '''Signup form vendors use to sign up for Beacon updates

    The goal here is to lower the barrier to signing up by as much as possible,
    making it as easy as possible to sign up. This means that very little of this
    information is required. This form is an implementation of the CategoryForm,
    which means that it processes categories and subcategories in addition to the
    below fields.

    Attributes:
        business_name: Name of business, required
        email: Email address of vendor signing up, required, must be unique
        first_name: First name of vendor, optional
        last_name: Last name of vendor, optional
        phone_number: Phone number of vendor, optional
        fax_number: Fax number of vendor, optional
        woman_owned: Whether the business is woman owned, optional
        minority_owned: Whether the business is minority owned, optional
        veteran_owned: Whether the business is veteran owned, optional
        disadvantaged_owned: Whether the business is disadvantaged owned, optional
        subscribed_to_newsletter: Boolean flag for whether a business
            is signed up to the receive the newsletter
    '''
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
    '''Signup form vendors can use for individual opportunities

    Attributes:
        business_name: Name of business, required
        email: Email address of vendor signing up, required, must be unique
        also_categories: Flag for whether or not a business should be signed up
            to receive updates about opportunities with the same categories as this one
    '''
    business_name = fields.TextField(validators=[DataRequired()])
    email = fields.TextField(validators=[DataRequired(), Email()])
    also_categories = fields.BooleanField()

class UnsubscribeForm(Form):
    '''Subscription management form, where Vendors can unsubscribe from all different emails

    Attributes:
        email: Email address of vendor signing up, required
        categories: A multicheckbox of all categories the Vendor
            is signed up to receive emails about
        opportunities: A multicheckbox of all opportunities the Vendor
            is signed up to receive emails about
        subscribed_to_newsletter: A flag for whether or not the Vendor should receive
            the biweekly update newsletter
    '''
    email = fields.TextField(validators=[DataRequired(), Email(), email_present])
    categories = MultiCheckboxField(coerce=int)
    opportunities = MultiCheckboxField(coerce=int)
    subscribed_to_newsletter = fields.BooleanField(
        label='Biweekly update on all opportunities posted to Beacon', validators=[Optional()],
        default='checked'
    )

class OpportunityDocumentForm(NoCSRFForm):
    '''Document subform for the main :py:class:`~purchasing.opportunities.forms.OpportunityForm`

    Attributes:
        title: Name of document to be uploaded
        document: Actual document file that should be uploaded
    '''
    title = fields.TextField(label='Document Name', validators=[RequiredIf('document')])
    document = FileField('Document', validators=[FileAllowed(
        ['pdf', 'doc', 'docx', 'xls', 'xlsx'],
        '.pdf, Word (.doc/.docx), and Excel (.xls/.xlsx) documents only!'),
        RequiredIf('title')]
    )

    def upload_document(self, _id):
        '''Take the document and filename and either upload it to S3 or the local uploads folder

        Arguments:
            _id: The id of the :py:class:`~purchasing.opportunities.models.Opportunity`
                the document will be attached to

        Returns:
            A two-tuple of (the document name, the document filepath/url)
        '''
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
    '''Form to create and edit individual opportunities

    This form is an implementation of the CategoryForm,
    which means that it processes categories and subcategories in addition to the
    below fields.

    Attributes:
        department: link to :py:class:`~purchasing.users.models.Department`
            that is primarily responsible for administering the RFP, required
        opportunity_type: link to :py:class:`~purchasing.data.contracts.ContractType` objects
            that have the ``allow_opportunities`` field set to True
        contact_email: Email address of the opportunity's point of contact for questions
        title: Title of the opportunity, required
        description: 500 or less word description of the opportunity, required
        planned_publish: Date when the opportunity should be made public on Beacon
        planned_submission_start: Date when the opportunity opens to accept responses
        planned_submission_end: Date when the opportunity closes and no longer
            accepts submissions
        vendor_documents_needed: A multicheckbox for all documents that a vendor
            might need to respond to this opportunity.
        documents: A list of :py:class:`~purchasing.opportunities.forms.OpportunityDocumentForm`
            fields.

    See Also:
        * :py:class:`~purchasing.data.contracts.ContractType`
            The ContractType model informs the construction of the "How to Bid"
            section in the template

        * :py:class:`~purchasing.opportunities.models.Opportunity`
            The base model that powers the form.
    '''
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
    planned_submission_end = DateTimeField(validators=[after_now, DataRequired()])
    vendor_documents_needed = QuerySelectMultipleField(
        widget=select_multi_checkbox,
        query_factory=RequiredBidDocument.generate_choices,
        get_pk=lambda i: i[0],
        get_label=lambda i: i[1]
    )
    documents = fields.FieldList(fields.FormField(OpportunityDocumentForm), min_entries=1)

    def display_cleanup(self, opportunity=None):
        '''Cleans up data for display in the form

        1. Builds the choices for the ``vendor_documents_needed``
        2. Formats the contact email for the form
        3. Localizes the ``planned_submission_end`` time

        See Also:
            :py:meth:`CategoryForm.display_cleanup`

        Arguments:
            opportunity: A :py:class:`purchasing.opportunities.model.Opportunity` object
                or None.
        '''
        self.vendor_documents_needed.choices = RequiredBidDocument.generate_choices()
        if opportunity and not self.contact_email.data:
            self.contact_email.data = opportunity.contact.email

        if self.planned_submission_end.data:
            self.planned_submission_end.data = pytz.UTC.localize(
                self.planned_submission_end.data
            ).astimezone(current_app.config['DISPLAY_TIMEZONE'])

        super(OpportunityForm, self).display_cleanup()

    def data_cleanup(self):
        '''Cleans up form data for processing and storage

        1. Pops off categories
        2. Pops off documents (they are handled separately)
        3. Sets the foreign keys Opportunity model relationships

        Returns:
            An ``opportunity_data`` dictionary, which can be used to
            instantiate or modify an :py:class:`~purchasing.opportunities.model.Opportunity`
            instance
        '''
        opportunity_data = self.pop_categories(categories=False)
        opportunity_data.pop('documents')

        opportunity_data['department_id'] = self.department.data.id
        opportunity_data['contact_id'] = parse_contact(opportunity_data.pop('contact_email'), self.department.data)
        opportunity_data['vendor_documents_needed'] = [int(i[0]) for i in opportunity_data['vendor_documents_needed']]
        return opportunity_data

    def process(self, formdata=None, obj=None, data=None, **kwargs):
        '''Processes category data and localizes ``planned_submission_end`` times

        See Also:
            :py:meth:`CategoryForm.process`
        '''
        super(OpportunityForm, self).process(formdata, obj, data, **kwargs)
        if self.planned_submission_end.data and formdata:
            self.planned_submission_end.data = current_app.config['DISPLAY_TIMEZONE'].localize(
                self.planned_submission_end.data
            ).astimezone(pytz.UTC).replace(tzinfo=None)
