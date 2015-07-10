# -*- coding: utf-8 -*-

from purchasing.database import db
from purchasing.opportunities.models import Category
from purchasing.data.importer import (
    extract, get_or_create, convert_empty_to_none
)

def parse_codes(codes):
    if codes is None:
        return codes

    codes_list = codes.split('|')
    if len(codes_list) == 1:
        return [int(codes)]
    else:
        return [int(i.strip()) for i in codes_list]

def parse_examples_tsv(examples):
    if examples is None:
        return examples

    else:
        return db.func.to_tsvector(' '.join([i.strip() for i in examples.split('|')]))

def main(file_target='./files/2015-05-27-nigp-cleaned.csv'):
    data = extract(file_target)

    for row in data:
        subcat, new_subcat = get_or_create(
            db.session, Category,
            nigp_codes=parse_codes(convert_empty_to_none(row.get('code'))),
            category=convert_empty_to_none(row.get('parent_category')),
            subcategory=convert_empty_to_none(row.get('category')),
            category_friendly_name=convert_empty_to_none(row.get('category_friendly_name')),
            examples=convert_empty_to_none(row.get('examples')),
            examples_tsv=parse_examples_tsv(convert_empty_to_none(row.get('examples')))
        )

        if new_subcat:
            db.session.add(subcat)

    db.session.commit()
