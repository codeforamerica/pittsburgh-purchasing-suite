# -*- coding: utf-8 -*-

from sqlalchemy.orm import backref
from sqlalchemy.schema import Table

from purchasing.database import db, Model, ReferenceCol, RefreshSearchViewMixin, Column
from purchasing.data.contracts import ContractBase

company_contract_association_table = Table(
    'company_contract_association', Model.metadata,
    Column('company_id', db.Integer, db.ForeignKey('company.id', ondelete='SET NULL'), index=True),
    Column('contract_id', db.Integer, db.ForeignKey('contract.id', ondelete='SET NULL'), index=True),
)

class Company(RefreshSearchViewMixin, Model):
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

class CompanyContact(RefreshSearchViewMixin, Model):
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


def get_all_companies_query():
    return db.session.query(db.distinct(Company.id).label('id'), Company.company_name).order_by(Company.company_name)

def assign_contract_to_company(contracts_list):
    for ix, contract in enumerate(contracts_list):
        if isinstance(contract, ContractBase):
            pass
        elif isinstance(contract, int):
            contracts_list[ix] = ContractBase.query.get(contract)
        else:
            raise Exception('Contract must be a Contract object or a contract id')

    return contracts_list
