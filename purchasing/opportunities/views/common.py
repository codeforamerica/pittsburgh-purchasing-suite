# -*- coding: utf-8 -*-

from flask import Blueprint
from collections import defaultdict

from purchasing.opportunities.forms import ValidationError
from purchasing.opportunities.models import Category

blueprint = Blueprint(
    'opportunities', __name__, url_prefix='/beacon',
    static_folder='../static', template_folder='../templates'
)

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

def fix_form_categories(request, form, cls, obj=None):
    '''Fix the incoming request form data to associate opps/vendors with categories

    Request - the flask request object
    form - the form whose data needs to be fixed
    cls - either Opportunity or Vendor, depending on the incoming context
    obj - the actual Opportunity or Vendor object
    '''
    form_data = {c.name: form.data.get(c.name, None) for c in cls.__table__.columns if c.name not in ['id', 'created_at']}
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
                if subcat is None:
                    raise ValidationError('{} is not a valid choice!'.format(subcat))
                form_data['categories'].add(subcat)

    return form_data
