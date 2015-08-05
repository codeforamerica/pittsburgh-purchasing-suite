# -*- coding: utf-8 -*-

from flask import render_template, current_app
from flask_mail import Message

from purchasing.extensions import mail

class Notification(object):
    def __init__(
        self, to_email=[], from_email=None, cc_email=[], subject='',
        html_template='/public/emails/email_admins.html',
        txt_template=None, convert_args=False, *args, **kwargs
    ):
        self.to_email = to_email
        self.from_email = from_email if from_email else current_app.config['MAIL_DEFAULT_SENDER']
        self.cc_email = cc_email
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
                recipients=recipient,
                cc=self.cc_email
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
