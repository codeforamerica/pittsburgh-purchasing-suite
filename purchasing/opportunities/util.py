# -*- coding: utf-8 -*-

from flask import session, current_app
from wtforms import widgets

from purchasing.database import db
from purchasing.notifications import Notification
from purchasing.users.models import User, Role
from purchasing.opportunities.models import Vendor, Opportunity

def parse_contact(contact_email, department):
    '''Finds or creates a :py:class:`purchasing.users.models.User` as the contact

    Arguments:
        contact_email: The email address of the user. If the user cannot
            be found in the database, the domain of their email must match the
            configured ``CITY_DOMAIN``
        department: The :py:class:`purchasing.users.models.Department` of the user

    Returns:
        The ID of the new/existing contact
    '''
    # get our department contact, build it if we don't have it yet
    contact = User.query.filter(User.email == contact_email).first()

    if contact is None:
        contact = User.create(
            email=contact_email,
            role=Role.query.filter(Role.name == 'staff').first(),
            department=department
        )

    return contact.id

def build_label_tooltip(name, description):
    '''Builds bootstrap-style tooltips for contract documents

    Arguments:
        name: The name of the document
        description: The description of the document -- lives in the
            tooltip and is shown on hover.

    Returns:
        A formatted label with tooltip
    '''
    return '''
    {} <i
        class="fa fa-question-circle"
        aria-hidden="true" data-toggle="tooltip"
        data-placement="right" title="{}">
    </i>'''.format(name, description)

def select_multi_checkbox(field, ul_class='', **kwargs):
    '''Custom multi-select widget for vendor documents needed

    Returns:
        SelectMulti checkbox with tooltip labels
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
        html.append(u'<label for="%s">%s</label>' % (choice_id, build_label_tooltip(name, description)))
        html.append(u'</div>')
    html.append(u'</div>')
    return u''.join(html)

class SignupData(object):
    '''Small python object to hold default data coming from the Flask session

    Arguments:
        email: Email address taken from session
        business_name: Business name taken from session
    '''

    def __init__(self, email, business_name):
        self.email = email
        self.business_name = business_name

def init_form(form, model=None):
    '''Initialize a form from either a given model or a
        :py:class:`purchasing.opportunities.util.SignupData` object

    Arguments:
        form: The form to initialize
        model: a Model used to instantiate the form with data

    Returns:
        The passed form, initialized with either the passed model
            or a new instance of
            :py:class:`purchasing.opportunities.util.SignupData`
    '''
    if model:
        return form(obj=model)
    else:
        data = SignupData(session.get('email'), session.get('business_name'))
        return form(obj=data)

def signup_for_opp(form, opportunity, multi=False):
    '''Sign a vendor up for an opportunity

    Generic helper method to handle subscriptions from both the list view
    (signing up form multiple opportunities) and the detail view (signing
    up for a single opportunity). Responsible for creation of new Vendor
    objects if necessary, and sending emails based on the opportunities
    selected to receive updates about.

    Arguments:
        form: The relevant subscription form
        opportunity: Either an opportunity model or a list of opportunity ids
        multi: A boolean to flag if there are multiple opportunities that should
            to subscribe to or a single opportunity

    Returns:
        True if email sent successfully, false otherwise
    '''
    send_email = True
    email_opportunities = []
    if opportunity is None or (isinstance(opportunity, list) and len(opportunity) == 0):
        form.errors['opportunities'] = ['You must select at least one opportunity!']
        return False
    # add the email/business name to the session
    session['email'] = form.data.get('email')
    session['business_name'] = form.data.get('business_name')
    # subscribe the vendor to the opportunity
    vendor = Vendor.query.filter(
        Vendor.email == form.data.get('email')
    ).first()

    if vendor is None:
        vendor = Vendor(
            email=form.data.get('email'),
            business_name=form.data.get('business_name')
        )
        db.session.add(vendor)
        db.session.commit()
    else:
        vendor.update(business_name=form.data.get('business_name'))

    if multi:
        for opp in opportunity:
            _opp = Opportunity.query.get(int(opp))
            if not _opp.is_public:
                db.session.rollback()
                form.errors['opportunities'] = ['That\'s not a valid choice.']
                return False
            if _opp in vendor.opportunities:
                send_email = False
            else:
                vendor.opportunities.add(_opp)
                email_opportunities.append(_opp)
    else:
        if opportunity in vendor.opportunities:
            send_email = False
        else:
            vendor.opportunities.add(opportunity)
            email_opportunities.append(opportunity)

    if form.data.get('also_categories'):
        # TODO -- add support for categories
        pass

    db.session.commit()

    current_app.logger.info(
        'OPPSIGNUP - Vendor has signed up for opportunities: EMAIL: {email} at BUSINESS: {bis_name} signed up for:\n' +
        'OPPORTUNITY: {opportunities}'.format(
            email=form.data.get('email'),
            business_name=form.data.get('business_name'),
            opportunities=', '.join([i.description for i in email_opportunities])
        )
    )

    if send_email:
        Notification(
            to_email=vendor.email,
            from_email=current_app.config['BEACON_SENDER'],
            subject='Subscription confirmation from Beacon',
            html_template='opportunities/emails/oppselected.html',
            txt_template='opportunities/emails/oppselected.txt',
            opportunities=email_opportunities
        ).send()

    return True
