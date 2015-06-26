# -*- coding: utf-8 -*-

from flask import current_app
import datetime
from purchasing.database import (
    Column,
    Model,
    db,
    ReferenceCol,
)
from sqlalchemy.schema import Table
from sqlalchemy.orm import backref
from sqlalchemy.dialects.postgres import ARRAY

category_vendor_association_table = Table(
    'category_vendor_association', Model.metadata,
    Column('category_id', db.Integer, db.ForeignKey('category.id', ondelete='SET NULL'), index=True),
    Column('vendor_id', db.Integer, db.ForeignKey('vendor.id', ondelete='SET NULL'), index=True)
)

category_opportunity_association_table = Table(
    'category_opportunity_association', Model.metadata,
    Column('category_id', db.Integer, db.ForeignKey('category.id', ondelete='SET NULL'), index=True),
    Column('opportunity_id', db.Integer, db.ForeignKey('opportunity.id', ondelete='SET NULL'), index=True)
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
    created_at = Column(db.DateTime, default=datetime.datetime.utcnow())
    department = Column(db.String(255))
    contact_id = ReferenceCol('users', ondelete='SET NULL')
    contact = db.relationship(
        'User', backref=backref('opportunities', lazy='dynamic'),
        foreign_keys='Opportunity.contact_id'
    )
    title = Column(db.String(255))
    description = Column(db.Text)
    categories = db.relationship(
        'Category',
        secondary=category_opportunity_association_table,
        backref='opportunities'
    )
    # Date department advertised bid
    planned_publish = Column(db.DateTime)
    # Date department opens bids
    planned_deadline = Column(db.DateTime)
    # Created from contract
    created_from_id = ReferenceCol('contract', ondelete='cascade', nullable=True)
    created_from = db.relationship('ContractBase', backref=backref(
        'opportunities', lazy='dynamic'
    ))
    documents_needed = Column(ARRAY(db.String(50)))
    document = Column(db.String(255))
    document_href = Column(db.String(255))
    created_by = ReferenceCol('users', ondelete='SET NULL')
    is_public = Column(db.Boolean(), default=True)

    def is_published(self):
        return self.planned_publish.date() >= datetime.date.today()

    def is_expired(self):
        return self.planned_deadline.date() >= datetime.date.today()

    def can_edit(self, user):
        '''Check if a user can edit the contract
        '''
        return False if user.is_anonymous() or (
            user.role.name not in ('conductor', 'admin', 'superadmin') and
            (user.id not in (self.created_by, self.contact_id))
        ) else True

    def get_href(self):
        '''Returns a proper link to a file
        '''
        if current_app.config['UPLOAD_S3']:
            return self.document_href
        else:
            if self.document_href.startswith('http'):
                return self.document_href
            return 'file://{}'.format(self.document_href)

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
