# -*- coding: utf-8 -*-

from purchasing.database import db
from purchasing.data.models import ContractBase, ContractProperty

from sqlalchemy.orm.session import make_transient

def create_new_contract(contract_data):
    '''
    Creates a new contract and any associated properties
    from contract_data and returns the contract
    '''
    properties = contract_data.pop('properties', [])
    contract = ContractBase.create(**contract_data)
    for property in properties:
        _property = property.items()[0]
        ContractProperty.create(**{
            'contract_id': contract.id, 'key': _property[0], 'value': _property[1]
        })

    return contract

def update_contract(contract_id, contract_data):
    '''
    Updates an individual contract and returns the contract
    '''
    contract = get_one_contract(contract_id)
    contract.update(**contract_data)
    return contract

def update_contract_property(contract_property_id, property_data):
    '''
    Updates a contract property and returns the property
    '''
    property = ContractProperty.query.get(contract_property_id)
    _property_data = property_data.items()[0]
    property.update(**{
        'contract': property.contract, 'key': _property_data[0], 'value': _property_data[1]
    })

    return property

def delete_contract(contract_id):
    '''
    Deletes a contract and all associated properties
    '''
    contract = get_one_contract(contract_id)
    contract.delete()
    return True

def get_one_contract(contract_id):
    '''
    Returns a contract associated with a contract ID
    '''
    contract = ContractBase.query.get(contract_id)
    return contract

def get_all_contracts():
    '''
    Returns a list of contracts.
    TODO: Paginate these results.
    '''
    return ContractBase.query.all()

def follow_a_contract(contract_id, user, field):
    '''
    Takes in a contract_id and a user model, and
    associates the user model with the relevant
    contract. This makes the user "follow" the
    contract for notification purposes. NOTE -
    normally we would just use the UPDATE method above,
    but because the user lives on an array, this would
    prevent multiple users from following one contract
    '''
    contract = get_one_contract(contract_id)
    if contract:
        if field == 'follow':
            if user not in contract.users:
                contract.users.append(user)
                return ('Successfully subscribed!', 'alert-success'), contract
            return ('Already subscribed!', 'alert-info'), contract
        elif field == 'star':
            if user not in contract.starred:
                contract.starred.append(user)
                return ('Successfully starred!', 'alert-success'), contract
            return ('Already starred', 'alert-info'), contract
    return None, None

def unfollow_a_contract(contract_id, user, field):
    '''
    Takes in a contract_id and a user model, and pops the
    user out of the list of users.
    '''
    contract = get_one_contract(contract_id)
    if contract:
        if field == 'follow':
            if user in contract.users:
                contract.users.remove(user)
                return ('Successfully unsubscribed', 'alert-success'), contract
            return ('You haven\'t subscribed to this contract!', 'alert-warning'), contract
        elif field == 'star':
            if user in contract.starred:
                contract.starred.remove(user)
                return ('Successfully unstarred', 'alert-success'), contract
            return ('You haven\'t starred this contract!', 'alert-warning'), contract
    return None, None

def clone_a_contract(contract):
    '''Takes a contract object and clones it

    The clone strips the following properties:
        + Financial ID
        + Expiration Date
        + Assigned To
        + Current Stage
        + Contract HREF

    Relationships are handled as follows:
        + Stars, Follows - moved to new contract (dropped from old)
        + Stage, Flow - Duplicated
        + Properties, Notes, Line Items, Companies kept on old
    '''
    old_contract_id = int(contract.id)

    subscribers = [
        ('follow', list(contract.users)),
        ('star', list(contract.starred))
    ]

    db.session.expunge(contract)
    make_transient(contract)

    contract.id = None
    contract.financial_id = None
    contract.expiration_date = None
    contract.assigned_to = None
    contract.current_stage = None
    contract.contract_href = None

    old_contract = get_one_contract(old_contract_id)
    # group everything that will rebuild the trigger
    # into one flush
    db.session.add(contract)
    old_contract.is_archived = True
    old_contract.description = old_contract.description + ' [Archived]'

    # we have to commit here in order to manage the relationships
    db.session.commit()

    for interaction, users in subscribers:
        for i in users:
            unfollow_a_contract(old_contract_id, i, interaction)
            follow_a_contract(contract.id, i, interaction)
            db.session.flush()

    db.session.commit()
    return contract
