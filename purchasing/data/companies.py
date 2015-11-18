# -*- coding: utf-8 -*-

from sqlalchemy.orm import backref
from sqlalchemy.schema import Table

from purchasing.database import db, Model, ReferenceCol, RefreshSearchViewMixin, Column

company_contract_association_table = Table(
    'company_contract_association', Model.metadata,
    Column('company_id', db.Integer, db.ForeignKey('company.id', ondelete='SET NULL'), index=True),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id', ondelete='SET NULL'), index=True),
)

class Company(RefreshSearchViewMixin, Model):
    '''Model for individual Compnaies

    Attributes:
        id: Primary key unique ID
        company_name: Name of the company
        contracts: Many-to-many relationship with the :py:class:`
            purchasing.data.contracts.ContractBase` model
    '''
    __tablename__ = 'company'

    id = Column(db.Integer, primary_key=True, index=True)
    company_name = Column(db.String(255), nullable=False, unique=True, index=True)
    contracts = db.relationship(
        'ContractBase',
        secondary=company_contract_association_table,
        backref='companies',
    )

    def __unicode__(self):
        return self.company_name

    @classmethod
    def all_companies_query_factory(cls):
        '''Query factory of all company ids and names ordered by name
        '''
        return db.session.query(
            db.distinct(cls.id).label('id'), cls.company_name
        ).order_by(cls.company_name)


class CompanyContact(RefreshSearchViewMixin, Model):
    '''Model for Company Contacts

    Attributes:
        id: Primary key unique ID
        company_id: Foreign key relationship to a :py:class:`~purchasing.data.companies.Company`
        company: Sqlalchemy relationship with a :py:class:`~purchasing.data.companies.Company`
        first_name: First name of the contact
        last_name: Last name of the contact
        addr1: First line of the contact's address
        addr2: Second line of the contract's address
        city: Contact address city
        state: Contact address state
        zip_code: Contact address zip code
        phone_number: Contact phone number
        fax_number: Contact fax number
        email: Contact email
    '''
    __tablename__ = 'company_contact'

    id = Column(db.Integer, primary_key=True, index=True)
    company = db.relationship(
        'Company',
        backref=backref('contacts', lazy='dynamic', cascade='all, delete-orphan')
    )
    company_id = ReferenceCol('company', ondelete='cascade')
    first_name = Column(db.String(255))
    last_name = Column(db.String(255))
    addr1 = Column(db.String(255))
    addr2 = Column(db.String(255))
    city = Column(db.String(255))
    state = Column(db.String(255))
    zip_code = Column(db.String(255))
    phone_number = Column(db.String(255))
    fax_number = Column(db.String(255))
    email = Column(db.String(255))

    def __unicode__(self):
        return '{first} {last}'.format(
            first=self.first_name, last=self.last_name
        )
