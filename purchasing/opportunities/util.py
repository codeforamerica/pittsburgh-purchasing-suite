# -*- coding: utf-8 -*-

from purchasing.users.models import User, Role

def parse_contact(contact_email, department):
    # get our department contact, build it if we don't have it yet
    contact = User.query.filter(User.email == contact_email).first()

    if contact is None:
        contact = User.create(
            email=contact_email,
            role=Role.query.filter(Role.name == 'staff').first(),
            department=department
        )

    return contact.id
