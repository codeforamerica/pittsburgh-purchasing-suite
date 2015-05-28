# -*- coding: utf-8 -*-

from flask import render_template, current_app
from flask_mail import Message
from purchasing.extensions import mail

def vendor_signup(vendor):
    '''
    Sends a signup notification to the email associated with a vendor object
    '''
    to_email = vendor.email

    msg = Message(
        subject='Thank you for signing up!',
        html=render_template('opportunities/emails/signup.html'),
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[to_email]
    )

    try:
        current_app.logger.debug('Attempting to send signup message to {}'.format(to_email))
        mail.send(msg)
        return True
    except Exception, e:
        current_app.logger.error('Attempted signup message to {} failed due to {}'.format(to_email, e))
        raise
