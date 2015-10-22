# -*- coding: utf-8 -*-

import pytz
import datetime

from flask import current_app

from purchasing.database import Column, Model, db, ReferenceCol
from purchasing.utils import localize_today

from sqlalchemy.schema import Table
from sqlalchemy.orm import backref
from sqlalchemy.dialects.postgres import ARRAY
from sqlalchemy.dialects.postgresql import TSVECTOR

from purchasing.notifications import Notification
from purchasing.utils import build_downloadable_groups, random_id
from purchasing.users.models import User, Role

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

opportunity_vendor_association_table = Table(
    'opportunity_vendor_association_table', Model.metadata,
    Column('opportunity_id', db.Integer, db.ForeignKey('opportunity.id', ondelete='SET NULL'), index=True),
    Column('vendor_id', db.Integer, db.ForeignKey('vendor.id', ondelete='SET NULL'), index=True)
)

class Category(Model):
    __tablename__ = 'category'

    id = Column(db.Integer, primary_key=True, index=True)
    nigp_codes = Column(ARRAY(db.Integer()))
    category = Column(db.String(255))
    subcategory = Column(db.String(255))
    category_friendly_name = Column(db.Text)
    examples = Column(db.Text)
    examples_tsv = Column(TSVECTOR)

    def __unicode__(self):
        return '{sub} (in {main})'.format(sub=self.category_friendly_name, main=self.category)

    @classmethod
    def parent_category_query_factory(cls):
        '''Return all of the parent categories
        '''
        return db.session.query(db.distinct(cls.category).label('category')).order_by('category')

    @classmethod
    def query_factory(cls):
        return cls.query

class Opportunity(Model):
    __tablename__ = 'opportunity'

    id = Column(db.Integer, primary_key=True)
    created_at = Column(db.DateTime, default=datetime.datetime.utcnow())
    department_id = ReferenceCol('department', ondelete='SET NULL', nullable=True)
    department = db.relationship(
        'Department', backref=backref('opportunities', lazy='dynamic')
    )
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
        backref='opportunities',
        collection_class=set
    )
    # Date opportunity should be made public on beacon
    planned_publish = Column(db.DateTime, nullable=False)
    # Date opportunity accepts responses
    planned_submission_start = Column(db.DateTime, nullable=False)
    # Date opportunity stops accepting responses
    planned_submission_end = Column(db.DateTime, nullable=False)
    # Created from contract
    created_from_id = ReferenceCol('contract', ondelete='cascade', nullable=True)

    # documents needed from the vendors
    vendor_documents_needed = Column(ARRAY(db.Integer()))

    # Whether opportunity is visible to non-City staff
    is_public = Column(db.Boolean(), default=False)

    # Archiving opportunities, mostly for removing duplicates in pending
    is_archived = Column(db.Boolean(), default=False)

    # Date opportunity was actually made public on beacon
    published_at = Column(db.DateTime, nullable=True)
    publish_notification_sent = Column(db.Boolean, default=False, nullable=False)

    opportunity_type_id = ReferenceCol('contract_type', ondelete='SET NULL', nullable=True)
    opportunity_type = db.relationship(
        'ContractType', backref=backref('opportunities', lazy='dynamic'),
    )

    def coerce_to_date(self, field):
        if isinstance(field, datetime.datetime):
            return field.date()
        if isinstance(field, datetime.date):
            return field
        return field

    def get_vendor_emails(self):
        return [i.email for i in self.vendors]

    @property
    def is_published(self):
        return self.coerce_to_date(self.planned_publish) <= localize_today() and self.is_public

    @property
    def is_upcoming(self):
        return self.coerce_to_date(self.planned_publish) <= localize_today() and \
            not self.is_submission_start and not self.is_submission_end and self.is_public

    @property
    def is_submission_start(self):
        return self.coerce_to_date(self.planned_submission_start) <= localize_today() and \
            self.coerce_to_date(self.planned_publish) <= localize_today() and \
            not self.is_submission_end and self.is_public

    @property
    def is_submission_end(self):
        return self.coerce_to_date(self.planned_submission_end) <= localize_today() and self.is_public

    @property
    def has_docs(self):
        return self.opportunity_documents.count() > 0

    def can_view(self, user):
        '''Check if a user can see opportunity detail
        '''
        return False if user.is_anonymous() and not self.is_published else True

    def can_edit(self, user):
        '''Check if a user can edit the contract
        '''
        if self.is_public and user.role.name in ('conductor', 'admin', 'superadmin'):
            return True
        elif not self.is_public and \
            (user.role.name in ('conductor', 'admin', 'superadmin') or
                user.id in (self.created_by_id, self.contact_id)):
                return True
        return False

    def estimate_submission_start(self):
        '''Returns the month/year based on planned_submission_start
        '''
        return self.planned_submission_start.strftime('%B %d, %Y')

    def estimate_submission_end(self):
        '''
        '''
        return pytz.UTC.localize(self.planned_submission_end).astimezone(
            current_app.config['DISPLAY_TIMEZONE']
        ).strftime('%B %d, %Y at %I:%M%p %Z')

    def get_needed_documents(self):
        return RequiredBidDocument.query.filter(
            RequiredBidDocument.id.in_(self.documents_needed)
        ).all()

    def get_events(self):
        '''Returns the dates out as a nice ordered list for rendering
        '''
        return [
            {
                'event': 'bid_submission_start', 'classes': 'event event-submission_start',
                'date': self.estimate_submission_start(),
                'description': 'Opportunity opens for submissions.'
            },
            {
                'event': 'bid_submission_end', 'classes': 'event event-submission_end',
                'date': self.estimate_submission_end(),
                'description': 'Deadline to submit proposals.'
            }
        ]

    def _handle_uploads(self, documents):
        opp_documents = self.opportunity_documents.all()

        for document in documents.entries:
            if document.title.data == '':
                continue

            _id = self.id if self.id else random_id(6)

            _file = document.document.data
            if _file.filename in [i.name for i in opp_documents]:
                continue

            filename, filepath = document.upload_document(_id)
            if filepath:
                self.opportunity_documents.append(OpportunityDocument(
                    name=document.title.data, href=filepath
                ))

    def _publish(self, publish):
        if not self.is_public:
            if publish:
                self.is_public = True

    def notify_approvals(self, user):
        Notification(
            to_email=[user.email],
            subject='Your post has been sent to OMB for approval',
            html_template='opportunities/emails/staff_postsubmitted.html',
            txt_template='opportunities/emails/staff_postsubmitted.txt',
            opportunity=self
        ).send(multi=True)

        Notification(
            to_email=db.session.query(User.email).join(Role, User.role_id == Role.id).filter(
                Role.name.in_(['conductor', 'admin', 'superadmin'])
            ).all(),
            subject='A new Beacon post needs review',
            html_template='opportunities/emails/admin_postforapproval.html',
            txt_template='opportunities/emails/admin_postforapproval.txt',
            opportunity=self
        ).send(multi=True)

    @classmethod
    def create(cls, data, user, documents, publish=False):
        opportunity = Opportunity(**data)

        current_app.logger.info(
'''BEACON NEW - New Opportunity Created: Department: {} | Title: {} | Publish Date: {} | Submission Start Date: {} | Submission End Date: {}
            '''.format(
                opportunity.id, opportunity.department.name if opportunity.department else '',
                opportunity.title.encode('ascii', 'ignore'),
                str(opportunity.planned_publish),
                str(opportunity.planned_submission_start), str(opportunity.planned_submission_end)
            )
        )

        if not (user.is_conductor() or publish):
            # only send 'your post has been sent/a new post needs review'
            # emails when 1. the submitter isn't from OMB and 2. they are
            # saving a draft as opposed to publishing the opportunity
            opportunity.notify_approvals(user)

        opportunity._handle_uploads(documents)
        opportunity._publish(publish)

        return opportunity

    def raw_update(self, **kwargs):
        super(Opportunity, self).update(**kwargs)

    def update(self, data, user, documents, publish=False):
        data.pop('publish_notification_sent', None)
        for attr, value in data.iteritems():
            setattr(self, attr, value)

        current_app.logger.info(
'''BEACON Update - Opportunity Updated: ID: {} | Title: {} | Publish Date: {} | Submission Start Date: {} | Submission End Date: {}
            '''.format(
                self.id, self.title.encode('ascii', 'ignore'), str(self.planned_publish),
                str(self.planned_submission_start), str(self.planned_submission_end)
            )
        )

        self._handle_uploads(documents)
        self._publish(publish)

    def send_publish_email(self):
        if self.is_published and not self.publish_notification_sent:
            opp_categories = [i.id for i in self.categories]

            vendors = Vendor.query.filter(
                Vendor.categories.any(Category.id.in_(opp_categories))
            ).all()

            Notification(
                to_email=[i.email for i in vendors],
                subject='A new City of Pittsburgh opportunity from Beacon!',
                html_template='opportunities/emails/newopp.html',
                txt_template='opportunities/emails/newopp.txt',
                opportunity=self
            ).send(multi=True)

            self.publish_notification_sent = True
            self.published_at = datetime.datetime.utcnow()

            current_app.logger.info(
'''BEACON PUBLISHED:  ID: {} | Title: {} | Publish Date: {} | Submission Start Date: {} | Submission End Date: {}
                '''.format(
                    self.id, self.title.encode('ascii', 'ignore'), str(self.planned_publish),
                    str(self.planned_submission_start), str(self.planned_submission_end)
                )
            )
            return True
        return False

class OpportunityDocument(Model):
    __tablename__ = 'opportunity_document'

    id = Column(db.Integer, primary_key=True, index=True)
    opportunity_id = ReferenceCol('opportunity', ondelete='cascade')
    opportunity = db.relationship(
        'Opportunity',
        backref=backref('opportunity_documents', lazy='dynamic', cascade='all, delete-orphan')
    )

    name = Column(db.String(255))
    href = Column(db.Text())

    def get_href(self):
        '''Returns a proper link to a file
        '''
        if current_app.config['UPLOAD_S3']:
            return self.href
        else:
            if self.href.startswith('http'):
                return self.href
            return 'file://{}'.format(self.href)

    def clean_name(self):
        '''Replaces underscores with spaces
        '''
        return self.name.replace('_', ' ')

class RequiredBidDocument(Model):
    __tablename__ = 'document'

    id = Column(db.Integer, primary_key=True, index=True)
    display_name = Column(db.String(255), nullable=False)
    description = Column(db.Text, nullable=False)
    form_href = Column(db.String(255))

    def get_choices(self):
        return (self.id, [self.display_name, self.description, self.form_href])

    @classmethod
    def query_factory(cls):
        return [i.get_choices() for i in cls.query.all()]

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
        backref='vendors',
        collection_class=set
    )
    opportunities = db.relationship(
        'Opportunity',
        secondary=opportunity_vendor_association_table,
        backref='vendors',
        collection_class=set
    )

    subscribed_to_newsletter = Column(db.Boolean(), default=False, nullable=False)

    @classmethod
    def newsletter_subscribers(cls):
        return cls.query.filter(cls.subscribed_to_newsletter == True).all()

    def build_downloadable_row(self):
        return [
            self.first_name, self.last_name, self.business_name,
            self.email, self.phone_number, self.minority_owned,
            self.woman_owned, self.veteran_owned, self.disadvantaged_owned,
            build_downloadable_groups('category_friendly_name', self.categories),
            build_downloadable_groups('title', self.opportunities)
        ]

    def __unicode__(self):
        return self.email
