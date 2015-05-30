# -*- coding: utf-8 -*-

import json
from collections import defaultdict

from flask import (
    Blueprint, render_template, url_for,
    jsonify, redirect, flash, request, session
)
from purchasing.database import db
from purchasing.notifications import vendor_signup
from purchasing.extensions import login_manager
from purchasing.opportunities.forms import SignupForm, UnsubscribeForm
from purchasing.opportunities.models import Category, Opportunity, Vendor

blueprint = Blueprint(
    'opportunities', __name__, url_prefix='/opportunities',
    static_folder='../static', template_folder='../templates'
)

@blueprint.route('/')
def index():
    '''
    Landing page for opportunities site
    '''
    return render_template(
        'opportunities/index.html'
    )

@blueprint.route('/signup', methods=['GET', 'POST'])
def signup():
    '''
    The signup page for vendors
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
        form_data['categories'] = [Category.query.get(i) for i in form.data.get('subcategories')]

        if vendor:
            vendor.update(
                **form_data
            )

            flash("You are already signed up! Your profile was updated with this new information", 'alert-info')

        else:
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
    '''
    Manage a vendor's signups
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

        for subscription in vendor.categories:
            form_subscriptions.append((subscription.id, subscription.subcategory))

    form.subscriptions.choices = form_subscriptions
    return render_template('opportunities/manage.html', form=form)
