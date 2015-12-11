# -*- coding: utf-8 -*-

import pytz
import datetime

from flask import current_app

from purchasing.database import Column, Model, db, ReferenceCol
from purchasing.utils import localize_today, localize_now

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
    '''Category model for opportunities and Vendor signups

    Categories are based on the codes created by the `National Institute
    of Government Purchasing (NIGP) <http://www.nigp.org/eweb/StartPage.aspx>`_.
    The names of the categories have been re-written a bit to make them more
    human-readable and in some cases a bit more modern.

    Attributes:
        id: Primary key unique ID
        nigp_codes: Array of integers refering to NIGP codes.
        category: parent top-level category
        subcategory: NIGP designated subcategory name
        category_friendly_name: Rewritten, more human-readable subcategory name
        examples: Pipe-delimited examples of items that fall in each subcategory
        examples_tsv: TSVECTOR of the examples for that subcategory

    See Also:
        The :ref:`nigp-importer` contains more information about how NIGP codes
        are imported into the system.
    '''
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
        '''Query factory to return a query of all of the distinct top-level categories
        '''
        return db.session.query(db.distinct(cls.category).label('category')).order_by('category')

    @classmethod
    def query_factory(cls):
        '''Query factory that returns all category/subcategory pairs
        '''
        return cls.query

class Opportunity(Model):
    '''Base Opportunity Model -- the central point for Beacon

    The Beacon model is centered around three dates:
    :py:attr:`~purchasing.opportunities.models.Opportunity.planned_publish`,
    :py:attr:`~purchasing.opportunities.models.Opportunity.planned_submission_start`,
    and :py:attr:`~purchasing.opportunities.models.Opportunity.planned_submission_end`.
    The publish date is when opportunities that are approved appear on Beacon. The
    publication date also is when vendors are notified via email.

    Attributes:
        id: Primary key unique ID
        title: Title of the Opportunity
        description: Short (maximum 500-word) description of the opportunity
        planned_publish: Date when the opportunity should show up on Beacon
        planned_submission_start: Date when vendors can begin submitting
            responses to the opportunity
        planned_submission_end: Deadline for submitted responses to the
            Opportunity
        vendor_documents_needed: Array of integers that relate to
            :py:class:`~purchasing.opportunities.models.RequiredBidDocument` ids
        is_public: True if opportunity is approved (publicly visible), False otherwise
        is_archived: True if opportunity is archived (not visible), False otherwise
        published_at: Date when an alert email was sent out to relevant vendors
        publish_notification_sent: True is notification sent, False otherwise
        department_id: ID of primary :py:class:`~purchasing.users.models.Department`
            for this opportunity
        department: Sqlalchemy relationship to primary
            :py:class:`~purchasing.users.models.Department`
            for this opportunity
        contact_id: ID of the :py:class:`~purchasing.users.models.User` for this opportunity
        contact: Sqlalchemy relationship to :py:class:`~purchasing.users.models.User`
            for this opportunity
        categories: Many-to-many relationship of the
            :py:class:`~purchasing.opportunities.models.Category` objects
            for this opportunity
        created_from_id: ID of the :py:class:`~purchasing.data.models.ContractBase`
            this opportunity was created from through Conductor
        opportunity_type_id: ID of the :py:class:`~purchasing.data.models.ContractType`
        opportunity_type: Sqlalchemy relationship to the :py:class:`~purchasing.data.models.ContractType`

    See Also:
        For more on the Conductor <--> Beacon relationship, look at the
        :py:func:`~purchasing.conductor.handle_form()` Conductor utility method and the
        :py:class:`~purchasing.conductor.forms.PostOpportunityForm` Conductor Form
    '''
    __tablename__ = 'opportunity'

    id = Column(db.Integer, primary_key=True)
    title = Column(db.String(255))
    description = Column(db.Text)
    planned_publish = Column(db.DateTime, nullable=False)
    planned_submission_start = Column(db.DateTime, nullable=False)
    planned_submission_end = Column(db.DateTime, nullable=False)
    vendor_documents_needed = Column(ARRAY(db.Integer()))
    is_public = Column(db.Boolean(), default=False)
    is_archived = Column(db.Boolean(), default=False, nullable=False)

    published_at = Column(db.DateTime, nullable=True)
    publish_notification_sent = Column(db.Boolean, default=False, nullable=False)

    department_id = ReferenceCol('department', ondelete='SET NULL', nullable=True)
    department = db.relationship(
        'Department', backref=backref('opportunities', lazy='dynamic')
    )

    contact_id = ReferenceCol('users', ondelete='SET NULL')
    contact = db.relationship(
        'User', backref=backref('opportunities', lazy='dynamic'),
        foreign_keys='Opportunity.contact_id'
    )

    categories = db.relationship(
        'Category',
        secondary=category_opportunity_association_table,
        backref='opportunities',
        collection_class=set
    )

    created_from_id = ReferenceCol('contract', ondelete='cascade', nullable=True)

    opportunity_type_id = ReferenceCol('contract_type', ondelete='SET NULL', nullable=True)
    opportunity_type = db.relationship(
        'ContractType', backref=backref('opportunities', lazy='dynamic'),
    )

    @classmethod
    def create(cls, data, user, documents, publish=False):
        '''Create a new opportunity

        Arguments:
            data: dictionary of fields needed to populate new
                opportunity object
            user: :py:class:`~purchasing.users.models.User` object
                creating the new opportunity
            documents: The documents FieldList from the
                :py:class:`~purchasing.opportunities.forms.OpportunityForm`

        Keyword Arguments:
            publish: Boolean as to whether to publish this document. If
                True, it will set ``is_public`` to True.

        See Also:
            The :py:class:`~purchasing.opportunities.forms.OpportunityForm`
            and :py:class:`~purchasing.opportunities.forms.OpportunityDocumentForm`
            have more information about the documents.

        '''
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
        '''Performs a basic update based on the passed kwargs.

        Arguments:
            **kwargs: Keyword arguments of fields to be updated in
                the existing Opportunity model
        '''
        super(Opportunity, self).update(**kwargs)

    def update(self, data, user, documents, publish=False):
        '''Performs an update, uploads new documents, and publishes

        Arguments:
            data: dictionary of fields needed to populate new
                opportunity object
            user: :py:class:`~purchasing.users.models.User` object
                updating the opportunity
            documents: The documents FieldList from the
                :py:class:`~purchasing.opportunities.forms.OpportunityForm`

        Keyword Arguments:
            publish: Boolean as to whether to publish this document. If
                True, it will set ``is_public`` to True.
        '''
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

    @property
    def is_published(self):
        '''Determine if an opportunity can be displayed

        Returns:
            True if the planned publish date is before or on today,
            and the opportunity is approved, False otherwise
        '''
        return self.coerce_to_date(self.planned_publish) <= localize_today() and self.is_public

    @property
    def is_upcoming(self):
        '''Determine if an opportunity is upcoming

        Returns:
            True if the planned publish date is before or on today, is approved,
            is not accepting submissions, and is not closed; False otherwise
        '''
        return self.coerce_to_date(self.planned_publish) <= localize_today() and \
            not self.is_submission_start and not self.is_submission_end and self.is_public

    @property
    def is_submission_start(self):
        '''Determine if the oppportunity is accepting submissions

        Returns:
            True if the submission start date and planned publish date are
            before or on today, is approved, and the opportunity is not closed;
            False otherwise
        '''
        return self.coerce_to_date(self.planned_submission_start) <= localize_today() and \
            self.coerce_to_date(self.planned_publish) <= localize_today() and \
            not self.is_submission_end and self.is_public

    @property
    def is_submission_end(self):
        '''Determine if an opportunity is closed to new submissions

        Returns:
            True if the submission end date is on or before today,
            and it is approved
        '''
        return pytz.UTC.localize(self.planned_submission_end).astimezone(
            current_app.config['DISPLAY_TIMEZONE']
        ) <= localize_now() and \
            self.is_public

    @property
    def has_docs(self):
        '''True if the opportunity has at least one document, False otherwise
        '''
        return self.opportunity_documents.count() > 0

    def estimate_submission_start(self):
        '''Returns the month/year based on submission start date
        '''
        return self.planned_submission_start.strftime('%B %d, %Y')

    def estimate_submission_end(self):
        '''Returns the localized date and time based on submission end date
        '''
        return pytz.UTC.localize(self.planned_submission_end).astimezone(
            current_app.config['DISPLAY_TIMEZONE']
        ).strftime('%B %d, %Y at %I:%M%p %Z')

    def can_view(self, user):
        '''Check if a user can see opportunity detail

        Arguments:
            user: A :py:class:`~purchasing.users.models.User` object

        Returns:
            Boolean indiciating if the user can view this opportunity
        '''
        return False if user.is_anonymous() and not self.is_published else True

    def can_edit(self, user):
        '''Check if a user can edit the contract

        Arguments:
            user: A :py:class:`~purchasing.users.models.User` object

        Returns:
            Boolean indiciating if the user can edit this opportunity.
            Conductors, the opportunity creator, and the primary opportunity
            contact can all edit the opportunity before it is published. After
            it is published, only conductors can edit it.
        '''
        if self.is_public and user.role.name in ('conductor', 'admin', 'superadmin'):
            return True
        elif not self.is_public and \
            (user.role.name in ('conductor', 'admin', 'superadmin') or
                user.id in (self.created_by_id, self.contact_id)):
                return True
        return False

    def coerce_to_date(self, field):
        '''Coerces the input field to a datetime.date object

        Arguments:
            field: A datetime.datetime or datetime.date object

        Returns:
            A datetime.date object
        '''
        if isinstance(field, datetime.datetime):
            return field.date()
        if isinstance(field, datetime.date):
            return field
        return field

    def get_vendor_emails(self):
        '''Return list of all signed up vendors
        '''
        return [i.email for i in self.vendors]

    def has_vendor_documents(self):
        '''Returns a Boolean for whether there are required bid documents

        See Also:
            :py:class:`~purchasing.opportunities.models.RequiredBidDocument`
        '''
        return self.vendor_documents_needed and len(self.vendor_documents_needed) > 0

    def get_vendor_documents(self):
        '''Returns a list of documents the the vendor will need to provide

        See Also:
            :py:class:`~purchasing.opportunities.models.RequiredBidDocument`
        '''
        if self.has_vendor_documents():
            return RequiredBidDocument.query.filter(
                RequiredBidDocument.id.in_(self.vendor_documents_needed)
            ).all()
        return []

    def get_events(self):
        '''Returns the opportunity dates out as a nice ordered list for rendering
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
        '''Send the approval notifications to everyone with approval rights

        Arguments:
            user: A :py:class:`~purchasing.users.models.User` object
        '''
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

    def send_publish_email(self):
        '''Sends the "new opportunity available" email to subscribed vendors

        If a new Opportunity is created and it has a publish date before or
        on today's date, it will trigger an immediate publish email send. This
        operates in a very similar way to the nightly
        :py:class:`~purchasing.jobs.beacon_nightly.BeaconNewOppotunityOpenJob`.
        It will build a list of all vendors signed up to the Opportunity
        or to any of the categories that describe the Opportunity.
        '''
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
    '''Model for bid documents associated with opportunities

    Attributes:
        id: Primary key unique ID
        opportunity_id: Foreign Key relationship back to the related
            :py:class:`~purchasing.opportunities.models.Opportunity`
        opportunity: Sqlalchemy relationship back to the related
            :py:class:`~purchasing.opportunities.models.Opportunity`
        name: Name of the document for display
        href: Link to the document
    '''
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
        '''Builds link to the file

        Returns:
            S3 link if using S3, local filesystem link otherwise
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
    '''Model for documents that a vendor would be required to provide

    There are two types of documents associated with an opportunity -- documents
    that the City will provide (RFP/IFB/RFQ, Q&A documents, etc.), and documents
    that the bidder will need to provide upon bidding (Insurance certificates,
    Bid bonds, etc.). This model describes the latter.

    See Also:
        These models get rendered into a select multi with the descriptions rendered
        in tooltips. For more on how this works, see the
        :py:func:`~purchasing.opportunities.utils.select_multi_checkbox`.

    Attributes:
        id: Primary key unique ID
        display_name: Display name for the document
        description: Description of what the document is, rendered in a tooltip
        form_href: A link to an example document
    '''
    __tablename__ = 'document'

    id = Column(db.Integer, primary_key=True, index=True)
    display_name = Column(db.String(255), nullable=False)
    description = Column(db.Text, nullable=False)
    form_href = Column(db.String(255))

    def get_choices(self):
        '''Builds a custom two-tuple for the CHOICES.

        Returns:
            Two-tuple of (ID, [name, description, href]), which can then be
            passed to :py:func:`~purchasing.opportunities.utils.select_multi_checkbox`
            to generate multi-checkbox fields
        '''
        return (self.id, [self.display_name, self.description, self.form_href])

    @classmethod
    def generate_choices(cls):
        '''Builds a list of custom CHOICES

        Returns:
            List of two-tuples described in the
            :py:meth:`RequiredBidDocument.get_choices`
            method
        '''
        return [i.get_choices() for i in cls.query.all()]

class Vendor(Model):
    '''Base Vendor model for businesses interested in Beacon

    The primary driving thought behind Beacon is that it should be as
    easy as possible to sign up to receive updates about new opportunities.
    Therefore, there are no Vendor accounts or anything like that, just
    email addresses and business names.

    Attributes:
        id: Primary key unique ID
        business_name: Name of the business, required
        email: Email address for the vendor, required
        first_name: First name of the vendor
        last_name: Last name of the vendor
        phone_number: Phone number for the vendor
        fax_number: Fax number for the vendor
        minority_owned: Whether the vendor is minority owned
        veteran_owned: Whether the vendor is veteran owned
        woman_owned: Whether the vendor is woman owned
        disadvantaged_owned: Whether the vendor is any class
            of Disadvantaged Business Enterprise (DBE)
        categories: Many-to-many relationship with
            :py:class:`~purchasing.opportunities.models.Category`;
            describes what the vendor is subscribed to
        opportunities: Many-to-many relationship with
            :py:class:`~purchasing.opportunities.models.Opportunity`;
            describes what opportunities the vendor is subscribed to
        subscribed_to_newsletter: Whether the vendor is subscribed to
            receive the biweekly newsletter of all opportunities
    '''
    __tablename__ = 'vendor'

    id = Column(db.Integer, primary_key=True, index=True)
    business_name = Column(db.String(255), nullable=False)
    email = Column(db.String(80), unique=True, nullable=False)
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
        '''Query to return all vendors signed up to the newsletter
        '''
        return cls.query.filter(cls.subscribed_to_newsletter == True).all()

    def build_downloadable_row(self):
        '''Take a Vendor object and build a list for a .tsv download

        Returns:
            List of all vendor fields in order for a bulk vendor download
        '''
        return [
            self.first_name, self.last_name, self.business_name,
            self.email, self.phone_number, self.minority_owned,
            self.woman_owned, self.veteran_owned, self.disadvantaged_owned,
            build_downloadable_groups('category_friendly_name', self.categories),
            build_downloadable_groups('title', self.opportunities)
        ]

    def __unicode__(self):
        return self.email
