# -*- coding: utf-8 -*-

import json
import datetime

from flask import (
    render_template, request, current_app, flash,
    redirect, url_for, session, abort, Blueprint
)
from flask_login import current_user

from purchasing.database import db
from purchasing.notifications import Notification
from purchasing.opportunities.forms import UnsubscribeForm, VendorSignupForm, OpportunitySignupForm
from purchasing.opportunities.models import Category, Opportunity, Vendor

from purchasing.opportunities.util import get_categories, fix_form_categories

from purchasing.users.models import User, Role

blueprint = Blueprint(
    'opportunities', __name__, url_prefix='/beacon',
    static_folder='../static', template_folder='../templates'
)

@blueprint.route('/')
def splash():
    '''Landing page for opportunities site
    '''
    return render_template(
        'opportunities/front/splash.html'
    )

@blueprint.route('/signup', methods=['GET', 'POST'])
def signup():
    '''The signup page for vendors
    '''
    all_categories = Category.query.all()
    form = init_form(VendorSignupForm)

    categories, subcategories, form = get_categories(all_categories, form)

    if form.validate_on_submit():

        vendor = Vendor.query.filter(Vendor.email == form.data.get('email')).first()
        form_data = fix_form_categories(request, form, Vendor, validate='subcategories', obj=vendor)
        if not form.errors:
            if vendor:
                current_app.logger.info('''
                    OPPPUPDATEVENDOR - Vendor updated:
                    EMAIL: {old_email} -> {email} at
                    BUSINESS: {old_bis} -> {bis_name} signed up for:
                    CATEGORIES:
                        {old_cats} ->
                        {categories}'''.format(
                    old_email=vendor.email, email=form_data['email'],
                    old_bis=vendor.business_name, bis_name=form_data['business_name'],
                    old_cats=[i.__unicode__() for i in vendor.categories],
                    categories=[i.__unicode__() for i in form_data['categories']]
                ))

                vendor.update(
                    **form_data
                )

                flash("You are already signed up! Your profile was updated with this new information", 'alert-info')

            else:
                current_app.logger.info(
                    'OPPNEWVENDOR - New vendor signed up: EMAIL: {email} at BUSINESS: {bis_name} signed up for:\n' +
                    'CATEGORIES: {categories}'.format(
                        email=form_data['email'],
                        bis_name=form_data['business_name'],
                        categories=[i.__unicode__() for i in form_data['categories']]
                    )
                )
                vendor = Vendor.create(
                    **form_data
                )

                confirmation_sent = Notification(
                    to_email=vendor.email, subject='Thank you for signing up!',
                    html_template='opportunities/emails/signup.html',
                    txt_template='opportunities/emails/signup.txt',
                    categories=form_data['categories']
                ).send()

                if confirmation_sent:
                    admins = db.session.query(User.email).join(Role).filter(
                        Role.name.in_(['admin', 'superadmin'])
                    ).all()

                    Notification(
                        to_email=admins, subject='A new vendor has signed up on beacon',
                        categories=form_data['categories'],
                        vendor=form_data['email'], convert_args=True,
                        business_name=form_data['business_name']
                    ).send()

                    flash('Thank you for signing up! Check your email for more information', 'alert-success')

                else:

                    flash('Uh oh, something went wrong. We are investigating.', 'alert-danger')

            session['email'] = form_data.get('email')
            session['business_name'] = form_data.get('business_name')
            return redirect(url_for('opportunities.splash'))

    page_email = request.args.get('email', None)

    if page_email:
        current_app.logger.info(
            'OPPSIGNUPVIEW - User clicked through to signup with email {}'.format(page_email)
        )
        session['email'] = page_email
        return redirect(url_for('opportunities.signup'))

    if 'email' in session:
        if not form.email.validate(form):
            session.pop('email', None)

    display_categories = subcategories.keys()
    display_categories.remove('Select All')

    return render_template(
        'opportunities/front/signup.html', form=form,
        subcategories=json.dumps(subcategories),
        categories=json.dumps(
            sorted(display_categories) + ['Select All']
        )
    )

@blueprint.route('/manage', methods=['GET', 'POST'])
def manage():
    '''Manage a vendor's signups
    '''
    form = init_form(UnsubscribeForm)
    form_categories = []
    form_opportunities = []

    if form.validate_on_submit():
        email = form.data.get('email')
        vendor = Vendor.query.filter(Vendor.email == email).first()

        if vendor is None:
            form.email.errors = ['We could not find the email {}'.format(email)]

        if request.form.get('button', '').lower() == 'unsubscribe from checked':
            remove_categories = set([Category.query.get(i) for i in form.categories.data])
            remove_opportunities = set([Opportunity.query.get(i) for i in form.opportunities.data])

            vendor.categories = vendor.categories.difference(remove_categories)
            vendor.opportunities = vendor.opportunities.difference(remove_opportunities)

            db.session.commit()
            flash('Preferences updated!', 'alert-success')

        if vendor:
            for subscription in vendor.categories:
                form_categories.append((subscription.id, subscription.category_friendly_name))
            for subscription in vendor.opportunities:
                form_opportunities.append((subscription.id, subscription.title))

    form.opportunities.choices = form_opportunities
    form.categories.choices = form_categories
    return render_template('opportunities/front/manage.html', form=form)

class SignupData(object):
    def __init__(self, email, business_name):
        self.email = email
        self.business_name = business_name

def init_form(form):
    data = SignupData(session.get('email'), session.get('business_name'))
    return form(obj=data)

def signup_for_opp(form, user, opportunity, multi=False):
    email_opportunities = []
    if opportunity is None or (isinstance(opportunity, list) and len(opportunity) == 0):
        form.errors['opportunities'] = ['You must select at least one opportunity!']
        return False
    # add the email/business name to the session
    session['email'] = form.data.get('email')
    session['business_name'] = form.data.get('business_name')
    # subscribe the vendor to the opportunity
    vendor = Vendor.query.filter(
        Vendor.email == form.data.get('email'),
        Vendor.business_name == form.data.get('business_name')
    ).first()

    if vendor is None:
        vendor = Vendor(
            email=form.data.get('email'),
            business_name=form.data.get('business_name')
        )
        db.session.add(vendor)
        db.session.commit()

    if multi:
        for opp in opportunity:
            _opp = Opportunity.query.get(int(opp))
            if not _opp.is_public:
                db.session.rollback()
                form.errors['opportunities'] = ['That\'s not a valid choice.']
                return False
            vendor.opportunities.add(_opp)
            email_opportunities.append(_opp)
    else:
        vendor.opportunities.add(opportunity)
        email_opportunities.append(opportunity)

    if form.data.get('also_categories'):
        # TODO -- add support for categories
        pass

    db.session.commit()

    Notification(
        to_email=vendor.email,
        subject='Subscription confirmation from Beacon',
        html_template='opportunities/emails/oppselected.html',
        txt_template='opportunities/emails/oppselected.txt',
        opportunities=email_opportunities
    ).send()
    return True

@blueprint.route('/opportunities', methods=['GET', 'POST'])
def browse():
    '''Browse available opportunities
    '''
    _open, upcoming = [], []

    signup_form = init_form(OpportunitySignupForm)
    if signup_form.validate_on_submit():
        opportunities = request.form.getlist('opportunity')
        if signup_for_opp(
            signup_form, current_user, opportunity=opportunities, multi=True
        ):
            flash('Successfully subscribed for updates!', 'alert-success')
            return redirect(url_for('opportunities.browse'))

    opportunities = Opportunity.query.filter(
        Opportunity.planned_deadline >= datetime.date.today()
    ).all()

    for opportunity in opportunities:
        if opportunity.is_open:
            _open.append(opportunity)
        elif opportunity.is_upcoming:
            upcoming.append(opportunity)

    return render_template(
        'opportunities/browse.html', opportunities=opportunities,
        _open=_open, upcoming=upcoming, current_user=current_user,
        signup_form=signup_form
    )

@blueprint.route('/opportunities/<int:opportunity_id>', methods=['GET', 'POST'])
def detail(opportunity_id):
    '''View one opportunity in detail
    '''
    opportunity = Opportunity.query.get(opportunity_id)
    if opportunity and (opportunity.is_public or not current_user.is_anonymous()):
        signup_form = init_form(OpportunitySignupForm)
        if signup_form.validate_on_submit():
            signup_success = signup_for_opp(signup_form, current_user, opportunity)
            if signup_success:
                flash('Successfully subscribed for updates!', 'alert-success')
                return redirect(url_for('opportunities.detail', opportunity_id=opportunity.id))

        has_docs = opportunity.opportunity_documents.count() > 0

        return render_template(
            'opportunities/front/detail.html', opportunity=opportunity,
            current_user=current_user, signup_form=signup_form, has_docs=has_docs
        )
    abort(404)
