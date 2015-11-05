# -*- coding: utf-8 -*-

from purchasing.database import db, Model, Column

class Stage(Model):
    __tablename__ = 'stage'

    id = Column(db.Integer, primary_key=True, index=True)
    name = Column(db.String(255))
    post_opportunities = Column(db.Boolean, default=False, nullable=False)

    default_message = Column(db.Text)

    def __unicode__(self):
        return self.name

    @classmethod
    def choices_factory(cls):
        return [(i.id, i.name) for i in cls.query.all()]
