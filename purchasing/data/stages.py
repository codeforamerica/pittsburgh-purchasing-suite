# -*- coding: utf-8 -*-

from purchasing.database import db, Model, Column

class Stage(Model):
    '''Model for individual conductor stages

    Attributes:
        id: Primary key unique ID
        name: Name of the stage
        post_opportunities: Whether you can post
            :py:class:`~purchasing.opportunities.models.Opportunity`
            objects to :doc:`/beacon` from this stage
        default_message: Message to autopopulate the
            :py:class:`~purchasing.conductor.forms.SendUpdateForm`
            message body
    '''
    __tablename__ = 'stage'

    id = Column(db.Integer, primary_key=True, index=True)
    name = Column(db.String(255))
    post_opportunities = Column(db.Boolean, default=False, nullable=False)
    default_message = Column(db.Text)

    def __unicode__(self):
        return self.name

    @classmethod
    def choices_factory(cls):
        '''Return a two-tuple of (stage id, stage name) for all stages
        '''
        return [(i.id, i.name) for i in cls.query.all()]
