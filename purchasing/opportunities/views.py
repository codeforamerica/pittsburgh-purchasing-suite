# -*- coding: utf-8 -*-

import json
from collections import defaultdict

from flask import (
    Blueprint, render_template, url_for,
    jsonify, redirect, flash, request, session
)
from purchasing.notifications import vendor_signup
from purchasing.extensions import login_manager
from purchasing.opportunities.forms import SignupForm
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
        subcategories[category.category].append((category.id, category.subcategory))

    form = SignupForm()

    form.categories.choices = [(None, '---')] + list(sorted(zip(categories, categories)))
    # form.subcategories.choices = sorted(subcategories['Apparel'])
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

            confirmation_sent = vendor_signup(vendor)

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

    return render_template(
        'opportunities/signup.html', form=form, subcategories=json.dumps(subcategories)
    )
