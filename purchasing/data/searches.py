# -*- coding: utf-8 -*-

from purchasing.database import db, Model, Column
from sqlalchemy.dialects.postgresql import TSVECTOR

class SearchView(Model):
    '''search_view is a materialized view with all of our text columns
    '''
    __tablename__ = 'search_view'

    id = Column(db.Text, primary_key=True, index=True)
    contract_id = Column(db.Integer)
    company_id = Column(db.Integer)
    financial_id = Column(db.String(255))
    expiration_date = Column(db.Date)
    contract_description = Column(db.Text)
    tsv_contract_description = Column(TSVECTOR)
    company_name = Column(db.Text)
    tsv_company_name = Column(TSVECTOR)
    detail_key = Column(db.Text)
    detail_value = Column(db.Text)
    tsv_detail_value = Column(TSVECTOR)
    line_item_description = Column(db.Text)
    tsv_line_item_description = Column(TSVECTOR)
