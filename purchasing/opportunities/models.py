# -*- coding: utf-8 -*-

import datetime
from purchasing.database import (
    Column,
    Model,
    db,
    ReferenceCol,
)

class Category(Model):
    __tablename__ = 'category'

    id = Column(db.Integer, primary_key=True, index=True)
    parent_category = Column(db.String(255))
    category = Column(db.String(255))

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
    created_from = db.relationship('ContractBase', lazy='dynamic', backref='opportunities')

class Vendor(Model):
    ___tablename__ = 'vendor'
    id = Column(db.Integer, nullable=False, unique=True, index=True)
    business_name = Column(db.String(255), nullable=False)
    email = Column(db.String(80), unique=True, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    first_name = Column(db.String(30), nullable=True)
    last_name = Column(db.String(30), nullable=True)
    phone_number = Column(db.Integer)
    fax_number = Column(db.Integer)
    minority_owned = Column(db.Boolean())
    veteran_owned = Column(db.Boolean())
    women_owned = Column(db.Boolean())
    disadvantaged_owned = Column(db.Boolean())

    def __unicode__(self):
        return self.email
