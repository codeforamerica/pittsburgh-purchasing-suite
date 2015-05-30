# -*- coding: utf-8 -*-

from flask import render_template, current_app, request
from flask_mail import Message
from purchasing.extensions import mail

def vendor_signup(vendor, categories=[]):
    '''
    Sends a signup notification to the email associated with a vendor object
    '''
    to_email = vendor.email

    msg_body = render_template('opportunities/emails/signup.html', categories=categories)
    txt_body = render_template('opportunities/emails/signup.txt', categories=categories)

    msg = Message(
        subject='Thank you for signing up!',
        body=txt_body,
        html=msg_body,
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[to_email]
    )

    try:
        current_app.logger.debug('Attempting to send signup message to {}'.format(to_email))
        mail.send(msg)
        return True
    except Exception, e:
        current_app.logger.error('Attempted signup message to {} failed due to {}'.format(to_email, e))
        return False
