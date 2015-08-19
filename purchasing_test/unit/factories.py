# -*- coding: utf-8 -*-

import datetime

import factory
from factory.alchemy import SQLAlchemyModelFactory

from purchasing.database import db
from purchasing.users.models import User, Role, Department
from purchasing.data.models import (
    Flow, Stage, StageProperty, ContractBase, ContractProperty,
    Company
)
from purchasing.opportunities.models import (
    Opportunity, RequiredBidDocument, OpportunityDocument, Category,
    Vendor
)

class BaseFactory(SQLAlchemyModelFactory):

    class Meta:
        abstract = True
        sqlalchemy_session = db.session

class RoleFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: '{}'.format(n))

    class Meta:
        model = Role

class DepartmentFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: 'department{}'.format(n))

    class Meta:
        model = Department

class UserFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)
    email = factory.Sequence(lambda n: '{}'.format(n))
    created_at = factory.Sequence(lambda n: datetime.datetime.now())
    first_name = factory.Sequence(lambda n: '{}'.format(n))
    last_name = factory.Sequence(lambda n: '{}'.format(n))
    department = factory.SubFactory(DepartmentFactory)
    active = factory.Sequence(lambda n: True)
    role = factory.SubFactory(RoleFactory)

    class Meta:
        model = User

class FlowFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)
    flow_name = factory.Sequence(lambda n: '{}'.format(n))
    stage_order = factory.Sequence(lambda n: n)

    class Meta:
        model = Flow

class StageFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: '{}'.format(n))
    post_opportunities = factory.Sequence(lambda n: n)

    class Meta:
        model = Stage

class StagePropertyFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)
    stage = factory.SubFactory(StageFactory)

    class Meta:
        model = StageProperty

class CompanyFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)

    class Meta:
        model = Company

class ContractBaseFactory(BaseFactory):
    id = factory.Sequence(lambda n: 100 + n)

    class Meta:
        model = ContractBase

class ContractPropertyFactory(BaseFactory):
    id = factory.Sequence(lambda n: n + 10)
    contract = factory.SubFactory(ContractBase)

    class Meta:
        model = ContractProperty

class CategoryFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)

    class Meta:
        model = Category

class OpportunityFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)
    department = factory.SubFactory(DepartmentFactory)

    class Meta:
        model = Opportunity

class VendorFactory(BaseFactory):
    id = factory.Sequence(lambda n: n)

    class Meta:
        model = Vendor

class RequiredBidDocumentFactory(BaseFactory):
    class Meta:
        model = RequiredBidDocument

class OpportunityDocumentFactory(BaseFactory):
    class Meta:
        model = OpportunityDocument
