# -*- coding: utf-8 -*-

import datetime
from purchasing.database import (
    Column,
    Model,
    db,
    ReferenceCol,
)
from sqlalchemy.schema import Table
from sqlalchemy.orm import backref

category_vendor_association_table = Table(
    'category_vendor_association', Model.metadata,
    Column('category_id', db.Integer, db.ForeignKey('category.id', ondelete='SET NULL'), index=True),
    Column('vendor_id', db.Integer, db.ForeignKey('vendor.id', ondelete='SET NULL'), index=True)
)

class Category(Model):
    __tablename__ = 'category'

    id = Column(db.Integer, primary_key=True, index=True)
    nigp_code = Column(db.Integer)
    category = Column(db.String(255))
    subcategory = Column(db.String(255))

    def __unicode__(self):
        return '{sub} (in {main})'.format(sub=self.subcategory, main=self.category)

class Opportunity(Model):
    __tablename__ = 'opportunity'

    id = Column(db.Integer, primary_key=True)
    contract_id = ReferenceCol('contract', ondelete='cascade')
    created_at = Column(db.DateTime, default=datetime.datetime.utcnow())

    # Also the opportunity open date
    title = Column(db.String(255))
    department = Column(db.String(255))
    # Autopopulated using title and department plus boilerplate copy?
    description = Column(db.Text)

    category_id = ReferenceCol('category', ondelete='SET NULL')
    category = db.relationship('Category', lazy='subquery')

    # Date department opens bids
    bid_open = Column(db.DateTime)

    # Created from contract
    created_from = db.relationship('ContractBase', lazy='subquery', backref='opportunities')

class Vendor(Model):
    __tablename__ = 'vendor'

    id = Column(db.Integer, primary_key=True, index=True)
    business_name = Column(db.String(255), nullable=False)
    email = Column(db.String(80), unique=True, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    first_name = Column(db.String(30), nullable=True)
    last_name = Column(db.String(30), nullable=True)
    phone_number = Column(db.String(20))
    fax_number = Column(db.String(20))
    minority_owned = Column(db.Boolean())
    veteran_owned = Column(db.Boolean())
    woman_owned = Column(db.Boolean())
    disadvantaged_owned = Column(db.Boolean())
    categories = db.relationship(
        'Category',
        secondary=category_vendor_association_table,
        backref='vendors'
    )

    def __unicode__(self):
        return self.email
