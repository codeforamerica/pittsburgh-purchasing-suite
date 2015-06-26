# -*- coding: utf-8 -*-

import json
from collections import defaultdict

from flask import (
    Blueprint, render_template, url_for, current_app,
    redirect, flash, request, session, abort
)
from flask_login import current_user
from purchasing.database import db
from purchasing.notifications import vendor_signup
from purchasing.extensions import login_manager
from purchasing.decorators import requires_roles
from purchasing.opportunities.forms import SignupForm, UnsubscribeForm, ValidationError, OpportunityForm
from purchasing.opportunities.models import Category, Opportunity, Vendor
from purchasing.users.models import User

blueprint = Blueprint(
    'opportunities', __name__, url_prefix='/opportunities',
    static_folder='../static', template_folder='../templates'
)

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

@blueprint.route('/')
def index():
    '''Landing page for opportunities site
    '''
    return render_template(
        'opportunities/index.html'
    )

@blueprint.route('/signup', methods=['GET', 'POST'])
def signup():
    '''The signup page for vendors
    '''
    all_categories = Category.query.all()
    categories, subcategories = set(), defaultdict(list)
    for category in all_categories:
        categories.add(category.category)
        subcategories['Select All'].append((category.id, category.subcategory))
        subcategories[category.category].append((category.id, category.subcategory))

    form = SignupForm()

    form.categories.choices = [(None, '---')] + list(sorted(zip(categories, categories))) + [('Select All', 'Select All')]
    form.subcategories.choices = []

    if form.validate_on_submit():

        vendor = Vendor.query.filter(Vendor.email == form.data.get('email')).first()
        form_data = {c.name: form.data.get(c.name, None) for c in Vendor.__table__.columns if c.name not in ['id', 'created_at']}
        form_data['categories'] = []
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
                    # make sure it's a valid subcategory
                    if subcat is None:
                        raise ValidationError('{} is not a valid choice!'.format(subcat))
                    form_data['categories'].append(subcat)

        if vendor:
            current_app.logger.info('OPPPUPDATEVENDOR - Vendor updated: EMAIL: {old_email} -> {email} at BUSINESS: {old_bis} -> {bis_name} signed up for:\n CATEGORIES: {old_cats} ->\n {categories}'.format(
                old_email=vendor.email,
                email=form_data['email'],
                old_bis=vendor.business_name,
                bis_name=form_data['business_name'],
                old_cats=[i.__unicode__() for i in vendor.categories],
                categories=[i.__unicode__() for i in form_data['categories']]
            ))

            vendor.update(
                **form_data
            )

            flash("You are already signed up! Your profile was updated with this new information", 'alert-info')

        else:
            current_app.logger.info(
                'OPPNEWVENDOR - New vendor signed up: EMAIL: {email} at BUSINESS: {bis_name} signed up for:\n CATEGORIES: {categories}'.format(
                    email=form_data['email'],
                    bis_name=form_data['business_name'],
                    categories=[i.__unicode__() for i in form_data['categories']]
                )
            )
            vendor = Vendor.create(
                **form_data
            )

            confirmation_sent = vendor_signup(vendor, categories=form_data['categories'])

            if confirmation_sent:
                flash('Thank you for signing up! Check your email for more information', 'alert-success')
            else:
                flash('Uh oh, something went wrong. We are investigating.', 'alert-danger')

        return redirect(url_for('opportunities.index'))

    page_email = request.args.get('email', None)

    if page_email:
        current_app.logger.info('OPPSIGNUPVIEW - User clicked through to signup with email {}'.format(page_email))
        session['email'] = page_email
        return redirect(url_for('opportunities.signup'))

    if 'email' in session:
        form.email.data = session['email']
        form.email.validate(form)
        session.pop('email')

    display_categories = subcategories.keys()
    display_categories.remove('Select All')

    return render_template(
        'opportunities/signup.html', form=form,
        subcategories=json.dumps(subcategories),
        categories=json.dumps(
            sorted(display_categories) + ['Select All']
        )
    )

@blueprint.route('/manage', methods=['GET', 'POST'])
def manage():
    '''Manage a vendor's signups
    '''
    form = UnsubscribeForm()
    form_subscriptions = []

    if form.validate_on_submit():
        email = form.data.get('email')
        vendor = Vendor.query.filter(Vendor.email == email).first()

        if vendor is None:
            form.email.errors = ['We could not find the email {}'.format(email)]

        if request.form.get('button', '').lower() == 'unsubscribe from checked':
            subscriptions = list(set([i.id for i in vendor.categories]).difference(form.subscriptions.data))
            vendor.categories = [Category.query.get(i) for i in subscriptions]
            db.session.commit()
            flash('Preferences updated!', 'alert-success')

        if vendor:
            for subscription in vendor.categories:
                form_subscriptions.append((subscription.id, subscription.subcategory))

    form.subscriptions.choices = form_subscriptions
    return render_template('opportunities/manage.html', form=form)

@blueprint.route('/opportunities', methods=['GET'])
def browse():
    '''Browse available opportunities
    '''
    opportunities = Opportunity.query.all()
    return render_template(
        'opportunities/browse.html', opportunities=opportunities,
        current_user=current_user
    )

@blueprint.route('/opportunities/<int:opportunity_id>')
def detail(opportunity_id):
    '''View one opportunity in detail
    '''
    pass

def build_opportunity(data, opportunity=None):
    contact_email = data.pop('contact_email')
    contact = User.query.filter(User.email == contact_email).first()

    if contact is None:
        contact = User().create(
            email=contact_email, role_id=2, department=data.get('department')
        )

    data.update(dict(contact_id=contact.id, created_by=current_user.id))

    if opportunity:
        opportunity = opportunity.update(**data)
    else:
        opportunity = Opportunity.create(**data)
    return opportunity

@blueprint.route('/admin/opportunities/new', methods=['GET', 'POST'])
# @requires_roles('staff', 'admin', 'superadmin', 'conductor')
def new():
    '''Create a new opportunity
    '''
    form = OpportunityForm()
    if form.validate_on_submit():
        opportunity = build_opportunity(form.data)
        flash('Opportunity Successfully Created!', 'alert-success')
        return redirect(url_for('opportunities.edit', opportunity_id=opportunity.id))
    return render_template('opportunities/opportunity.html', form=form, opportunity=None)

@blueprint.route('/admin/opportunities/<int:opportunity_id>/edit', methods=['GET', 'POST'])
# @requires_roles('staff', 'admin', 'superadmin', 'conductor')
def edit(opportunity_id):
    '''Edit an opportunity
    '''
    opportunity = Opportunity.query.get(opportunity_id)
    if opportunity:
        form = OpportunityForm(obj=opportunity)
        form.contact_email.data = opportunity.contact.email
        if form.validate_on_submit():
            build_opportunity(form.data, opportunity=opportunity)
            flash('Opportunity Successfully Updated!', 'alert-success')
            return redirect(url_for('opportunities.edit', opportunity_id=opportunity.id))
        return render_template(
            'opportunities/opportunity.html', form=form, opportunity=opportunity
        )
    abort(404)
