# -*- coding: utf-8 -*-

from purchasing.database import Column, Model, db

class AppStatus(Model):
    __tablename__ = 'app_status'

    id = Column(db.Integer, primary_key=True)
    status = Column(db.String(255))
    last_updated = Column(db.DateTime)
    county_max_deadline = Column(db.DateTime)
    message = Column(db.Text)
