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
    __tablename__ = 'accepted_domains'

    id = Column(db.Integer, primary_key=True)
    domain = Column(db.String(255), unique=True)

    @classmethod
    def valid_domain(cls, domain_to_lookup):
        '''Check if a domain is in the valid domains

        :param domain_to_lookup: string of domain to be checked
        :return: Boolean if domain is valid
        '''
        return cls.query.filter(
            str(domain_to_lookup).lower() == db.func.lower(cls.domain)
        ).count() > 0
