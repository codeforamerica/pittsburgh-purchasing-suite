# -*- coding: utf-8 -*-

from purchasing.database import db
from purchasing.opportunities.models import Category
from purchasing.data.importer import (
    extract, get_or_create, convert_empty_to_none
)

def main(file_target='./files/2015-05-27-nigp-cleaned.csv'):
    data = extract(file_target)

    for row in data:
        subcat, new_subcat = get_or_create(
            db.session, Category,
            nigp_code=convert_empty_to_none(row.get('code')),
            category=convert_empty_to_none(row.get('parent_category')),
            subcategory=convert_empty_to_none(row.get('category'))
        )

        if new_subcat:
            db.session.add(subcat)

    db.session.commit()
