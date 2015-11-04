# -*- coding: utf-8 -*-

from purchasing.database import Column, Model, db

class AppStatus(Model):
    __tablename__ = 'app_status'

    id = Column(db.Integer, primary_key=True)
    status = Column(db.String(255))
    last_updated = Column(db.DateTime)
    county_max_deadline = Column(db.DateTime)
    message = Column(db.Text)
    last_beacon_newsletter = Column(db.DateTime)

class AcceptedEmailDomains(Model):
    '''Model of permitted email domains for new user creation

    Because authentication is handled by `persona
    <https://login.persona.org/about>`_, we still need to control
    some level of authorization. We do this on two levels. First,
    we use Role-based permissions using the :py:class:`~purchasing.data.models.Role`
    class and the :py:func:`~purchasing.decorators.requires_roles` method.
    We also do this by restricting new user creation to people who have
    a certain set of email domains.

    Arguments:
        id (int): Primary key
        domain (str): string of an acceptable domain (for example, ``pittsburghpa.gov``)
    '''
    __tablename__ = 'accepted_domains'

    id = Column(db.Integer, primary_key=True)
    domain = Column(db.String(255), unique=True)

    @classmethod
    def valid_domain(cls, domain_to_lookup):
        '''Check if a domain is in the valid domains

        Args:
            domain_to_lookup (str): string of domain to be checked

        Returns:
            bool: True if domain is valid, False otherwise
        '''
        return cls.query.filter(
            str(domain_to_lookup).lower() == db.func.lower(cls.domain)
        ).count() > 0
