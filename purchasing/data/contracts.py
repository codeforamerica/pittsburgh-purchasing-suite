# -*- coding: utf-8 -*-

from purchasing.database import db
from purchasing.data.models import ContractBase, ContractProperty
from purchasing.opportunities.models import Opportunity

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

def extend_a_contract(child_contract_id=None, delete_child=True):
    '''Extends a contract.

    Because conductor clones existing contracts when work begins,
    when we get an "extend" signal, we actually want to extend the
    parent conract of the clone. Optionally (by default), we also
    want to delete the child (cloned) contract.
    '''
    child_contract = get_one_contract(child_contract_id)
    parent_contract = child_contract.parent

    parent_contract.expiration_date = None

    # strip the flow -- this will serve as the flag that
    # the contract is extended

    if delete_child:
        delete_contract(child_contract_id)

    return parent_contract

def transfer_contract_relationships(parent_contract, child_contract):
    '''Transfers stars/follows from parent to child contract
    '''

    for user in list(parent_contract.followers):
        child_contract.add_follower(user)
        parent_contract.remove_follower(user)

    return child_contract

def complete_contract(parent_contract, child_contract):
    transfer_contract_relationships(parent_contract, child_contract)

    parent_contract.is_archived = True
    parent_contract.is_visible = False

    if not parent_contract.description.endswith(' [Archived'):
        parent_contract.description += ' [Archived]'

    child_contract.is_archived = False
    child_contract.is_visible = True

    return child_contract

def clone_a_contract(contract, parent_id=None, strip=True, new_conductor_contract=True):
    '''Takes a contract object and clones it

    The clone always strips the following properties:
        + Assigned To
        + Current Stage

    If the strip flag is set to true, the following are also stripped
        + Contract HREF
        + Financial ID
        + Expiration Date

    If the new_conductor_contract flag is set to true, the following are set:
        + is_visible set to False
        + is_archived set to False

    Relationships are handled as follows:
        + Stage, Flow - Duplicated
        + Properties, Notes, Line Items, Companies, Stars, Follows kept on old
    '''
    old_contract_id = int(contract.id)

    db.session.expunge(contract)
    make_transient(contract)

    contract.id = None
    contract.assigned_to = None
    contract.current_stage = None
    contract.contract_href = None

    if strip:
        contract.financial_id = None
        contract.expiration_date = None

    if new_conductor_contract:
        contract.is_archived = False
        contract.is_visible = False

    # set the parent
    if parent_id:
        contract.parent_id = parent_id
    else:
        contract.parent_id = old_contract_id

    db.session.add(contract)
    db.session.commit()
    return contract
