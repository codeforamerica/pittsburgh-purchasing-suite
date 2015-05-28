# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, url_for,
    jsonify, redirect, flash
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
    categories, subcategories = set(), []
    for category in all_categories:
        categories.add(category.category)
        if category.category == 'Apparel':
            subcategories.append(category.subcategory)

    form = SignupForm()

    form.categories.choices = sorted(zip(categories, categories))
    form.subcategories.choices = sorted(zip(subcategories, subcategories))

    if form.validate_on_submit():

        vendor = Vendor.query.filter(Vendor.email == form.data.get('email')).first()
        form_data = {c.name: form.data.get(c.name, None) for c in Vendor.__table__.columns if c.name not in ['id', 'created_at']}

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

    return render_template(
        'opportunities/signup.html', form=form
    )

@blueprint.route('/_data/signup/subcategories/<category>')
def subcategory(category):
    '''
    Data view to show all subcategories for a particular parent category
    '''
    subcategories = Category.query.filter(Category.category == category).all()

    return jsonify({
        'results': [i.as_dict() for i in subcategories]
    })
