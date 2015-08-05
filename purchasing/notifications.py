# -*- coding: utf-8 -*-

from flask import render_template, current_app
from flask_mail import Message

from purchasing.extensions import mail
from purchasing.users.models import User, Role

class Notification(object):
    def __init__(
        self, to_email=[], from_email=None, subject='',
        html_template='/public/emails/email_admins.html',
        txt_template=None, convert_args=False, *args, **kwargs
    ):
        self.to_email = to_email
        self.from_email = from_email if from_email else current_app.config['MAIL_DEFAULT_SENDER']
        self.subject = subject
        self.html_body = self.build_msg_body(html_template, convert_args, *args, **kwargs)
        if txt_template:
            self.txt_body = self.build_msg_body(txt_template, convert_args, *args, **kwargs)
        else:
            self.txt_body = ''

    def build_msg_body(self, template, convert_args, *args, **kwargs):
        if convert_args:
            return render_template(template, kwargs=self.convert_models(dict(kwargs)))
        return render_template(template, *args, **kwargs)

    def convert_models(self, kwarg_dict):
        for key, value in kwarg_dict.iteritems():
            if isinstance(value, (set, list)):
                tmp_list = []
                for v in value:
                    tmp_list.append(v.__unicode__())
                kwarg_dict[key] = '; '.join(tmp_list)
            else:
                pass

        return kwarg_dict

    def _send(self, conn, recipient):
        try:
            current_app.logger.debug(
                'EMAILTRY | Sending message:\nTo: {}\n:From: {}\nSubject: {}'.format(
                    self.to_email, self.from_email, self.subject
                )
            )

            if isinstance(recipient, list):
                pass
            else:
                recipient = [recipient]

            msg = Message(
                subject='[Pittsburgh Purchasing] {}'.format(self.subject),
                html=self.html_body, body=self.txt_body,
                sender=self.from_email,
                recipients=recipient
            )

            conn.send(msg)
            return True
        except Exception, e:
            current_app.logger.debug(
                'EMAILFAIL | Error: {}\nTo: {}\n:From: {}\nSubject: {}'.format(
                    e, self.to_email, self.from_email, self.subject
                )
            )
            return False

    def send(self, multi=False):
        if multi:
            with mail.connect() as conn:
                for to in self.to_email:
                    if not self._send(conn, to):
                        return False
        else:
            if not self._send(mail, self.to_email):
                return False

        return True

def vendor_signup(vendor, categories=[]):
    '''Sends a signup notification to the email associated with a vendor object
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
        current_app.logger.debug('SIGNUPTRY | Attempting to send signup message to {}'.format(
            to_email)
        )
        mail.send(msg)
        return True
    except Exception, e:
        current_app.logger.error('SIGNUPFAIL | Attempted signup message to {} failed due to {}'.format(
            to_email, e)
        )
        return False

def wexplorer_feedback(contract, sender, body):
    '''Sends a notification to the configured ADMIN_EMAIL.
    '''
    msg_body = render_template('wexplorer/feedback_email.html', contract=contract, sender=sender, body=body)

    msg = Message(
        subject='Wexplorer contract feedback - ID: {id}, Description: {description}'.format(
            id=contract.id,
            description=contract.description
        ),
        html=msg_body,
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[current_app.config['ADMIN_EMAIL']]
    )

    try:
        current_app.logger.debug('WEXFEEDBACK | Attempting to send Wexplorer feedback about ID: {id}'.format(
            id=contract.id)
        )
        mail.send(msg)
        return True
    except Exception, e:
        current_app.logger.error(
            'WEXFEEDBACKERROR | Attempted to send Wexplorer feedback about ID: {id} failed due to {e}'.format(
                id=contract.id, e=e
            )
        )
        return False

def new_contract_autoupdate(contract, sender):
    '''Bulk mails all users following a contract with information about their new contract
    '''
    msg_body = render_template('conductor/emails/new_contract.html', contract=contract)

    with mail.connect() as conn:
        for user in contract.followers:
            msg = Message(
                subject='[Pittsburgh Procurement] A contract you follow has been updated!',
                html=msg_body,
                sender=sender,
                recipients=[user.email]
            )

            conn.send(msg)

def send_conductor_alert(send_to, subject, body, sender):
    '''Trigger email sent from the conductor workflow
    '''
    msg_body = render_template('conductor/emails/email_update.html', body=body)

    msg = Message(
        subject='[Pittsburgh Procurement] {}'.format(subject),
        html=msg_body,
        sender=sender,
        recipients=[send_to]
    )

    mail.send(msg)
    return True

def convert_models():
    pass

def notify_site_admins(subject, message, sender=None, *args, **kwargs):
    '''Trigger email sent to site admins
    '''
    msg_body = render_template(
        '/public/emails/email_admins.html',
        message=message,
        kwargs=convert_models(dict(kwargs))
    )

    with mail.connect() as conn:
        for user in User.query.join(Role).filter(Role.name.in_(['admin', 'superadmin'])).all():
            msg = Message(
                subject='[Pittsburgh Purchasing] {}'.format(subject),
                html=msg_body,
                sender=sender if sender else current_app.config['MAIL_DEFAULT_SENDER'],
                recipients=[user.email]
            )

            conn.send(msg)
        return True
