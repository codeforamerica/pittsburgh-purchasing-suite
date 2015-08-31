# -*- coding: utf-8 -*-

import collections

from werkzeug import secure_filename
from werkzeug.datastructures import FileStorage

from flask import render_template, current_app
from flask_mail import Message

from purchasing.compat import basestring
from purchasing.extensions import mail

class Notification(object):
    def __init__(
        self, to_email=[], from_email=None, cc_email=[], subject='',
        html_template='/public/emails/email_admins.html',
        txt_template=None, attachments=[],
        convert_args=False, *args, **kwargs
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
        self.attachments = attachments

    def build_msg_body(self, template, convert_args, *args, **kwargs):
        if convert_args:
            return render_template(template, kwargs=self.convert_models(dict(kwargs)))
        return render_template(template, *args, **kwargs)

    def convert_models(self, kwarg_dict):
        for key, value in kwarg_dict.iteritems():
            if isinstance(value, (set, list)):
                tmp_list = []
                for v in value:
                    if hasattr(v, '__unicode__'):
                        tmp_list.append(v.__unicode__())
                    else:
                        tmp_list.append(v)
                kwarg_dict[key] = '; '.join(tmp_list)
            else:
                pass

        return kwarg_dict

    def _flatten(self, l):
        '''Returns a flat generator object from artibrary-depth iterables
        '''
        for el in l:
            if isinstance(el, collections.Iterable) and not isinstance(el, basestring):
                for sub in self._flatten(el):
                    yield sub
            else:
                yield el

    def flatten(self, l):
        '''Coerces the generator from _flatten to a list and return it
        '''
        return list(self._flatten(l))

    def _send(self, conn, recipient):
        try:
            current_app.logger.debug(
                'EMAILTRY | Sending message:\nTo: {}\n:From: {}\nSubject: {}'.format(
                    self.to_email, self.from_email, self.subject
                )
            )

            if isinstance(recipient, str) or isinstance(recipient, unicode):
                recipient = [recipient]
            elif isinstance(recipient, collections.Iterable):
                recipient = self.flatten(recipient)
            else:
                raise Exception('Unsupported recipient type: {}'.format(type(recipient)))

            msg = Message(
                subject='[Pittsburgh Purchasing] {}'.format(self.subject),
                html=self.html_body, body=self.txt_body,
                sender=self.from_email,
                recipients=recipient,
                cc=self.cc_email
            )

            for attachment in self.attachments:
                if isinstance(attachment, FileStorage):
                    msg.attach(
                        filename=secure_filename(attachment.filename),
                        content_type=attachment.content_type,
                        data=attachment.stream.read()
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
