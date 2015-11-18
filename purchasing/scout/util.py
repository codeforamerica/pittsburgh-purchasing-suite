# -*- coding: utf-8 -*-

import datetime

from flask import current_app, flash, redirect, url_for, render_template
from purchasing.extensions import db

from purchasing.notifications import Notification

from purchasing.scout.forms import FeedbackForm, SearchForm
from purchasing.users.models import Department, User, Role
from purchasing.data.contracts import ContractBase
from purchasing.data.searches import SearchView

from flask_login import current_user

# build filter and filter form
FILTER_FIELDS = [
    ('company_name', 'Company Name', SearchView.tsv_company_name),
    ('line_item', 'Line Item', SearchView.tsv_line_item_description),
    ('contract_description', 'Contract Description', SearchView.tsv_contract_description),
    ('contract_detail', 'Contract Detail', SearchView.tsv_detail_value),
    ('financial_id', 'Controller Number', SearchView.financial_id),
]

def build_filter(req_args, fields, search_for, filter_form, _all):
    '''Build the non-exclusive filter conditions for scout search

    Along with building the filter for the search, build_filter also modifies
    the passed in ``filter_form``, setting the *checked* property on the appropriate
    form fields.

    Arguments:
        req_args: request.args from Flask.request
        fields: list of three-tuples. Each three-tuple should contain the following:

                * database column name
                * desired output display name
                * Model property that maps to the specific column name in question.

            For build_filter, only the column name and Model property are used. For :func:`build_cases`, all are used.

        search_for: string search term
        filter_form:
        _all: Boolean -- true if we are searching across all fields, false otherwise

    Returns:
        List of clauses that can be used in `Sqlalchemy query filters`_
    '''
    clauses = []
    for arg_name, _, filter_column in fields:
        if _all or req_args.get(arg_name) == 'y':
            if not _all:
                filter_form[arg_name].checked = True
            clauses.append(filter_column.match(
                search_for,
                postgresql_regconfig='english')
            )
    return clauses

def build_cases(req_args, fields, search_for, _all):
    '''Build case statements for categorizing search matches in scout search

    Arguments:
        req_args: request.args from Flask.request
        fields: list of three-tuples. Each three-tuple should contain the following:

                * database column name
                * desired output display name
                * Model property that maps to the specific column name in question.

            For build_cases, all three parts of the tuple are used

        search_for: string search term
        _all: Boolean -- true if we are searching across all fields, false otherwise

    Returns:
        List of clauses that can be used in a
        `Sqlalchemy case expressions`_
    '''
    clauses = []
    for arg_name, arg_description, filter_column in fields:
        if _all or req_args.get(arg_name) == 'y':
            clauses.append(
                (filter_column.match(
                    search_for,
                    postgresql_regconfig='english'
                ) == True, arg_description)
            )
    return clauses

def feedback_handler(contract, search_for=None):
    '''Allow user to send feedback on the data present in a specific contract

    Arguments:
        contract: :py:class:`~purchasing.data.contracts.ContractBase` object
        search_for: search term or None.

    Returns:
        Redirects to or renders the appropriate feedback handling template
    '''
    form = FeedbackForm()
    search_form = SearchForm()

    if not current_user.is_anonymous():
        form.sender.data = current_user.email

    if form.validate_on_submit():

        current_app.logger.info('WEXFEEDBACK - Feedback from {email} about {contract}'.format(
            email=form.sender.data,
            contract=contract.description
        ))

        feedback_sent = Notification(
            to_email=db.session.query(User.email).join(Role, User.role_id == Role.id).filter(
                Role.name.in_(['admin', 'superadmin'])
            ).all(),
            subject='Scout contract feedback - ID: {id}, Description: {description}'.format(
                id=contract.id if contract.id else 'N/A',
                description=contract.description
            ), html_template='scout/feedback_email.html',
            contract=contract, sender=form.data.get('sender'),
            body=form.data.get('body')
        ).send()

        if feedback_sent:
            flash('Thank you for your feedback!', 'alert-success')
        else:
            flash('Oh no! Something went wrong. We are looking into it.', 'alert-danger')

        if contract.id:
            return redirect(url_for('scout.contract', contract_id=contract.id))
        return redirect(url_for('scout.explore'))

    return render_template(
        'scout/feedback.html',
        search_form=search_form,
        contract=contract,
        choices=Department.choices(),
        feedback_form=form,
        search_for=search_for
    )

def add_archived_filter(query, archived):
    '''Adds exclusionary filters and archived contracts to contract searches.

    All searches exclude invalid contract objects, such as ones that have no
    financial id or no expiration date. Occasionally, the user will also want
    to search expired contracts. If the flag is passed, "archived" contracts, (which
    are either expired or manually flagged as no longer usuable) are shown as well.

    Arguments:
        query: Sqlalchemy contract search query
        archived: Boolean to determine if archived contracts should be included in search results

    Returns:
        Original query with additional exclusionary filters and optionally archived contracts
    '''
    query = query.filter(
        ContractBase.financial_id != None,
        ContractBase.expiration_date != None,
        SearchView.expiration_date != None
    )

    if not archived:
        query = query.filter(
            ContractBase.is_archived == False,
            ContractBase.expiration_date >= datetime.date.today(),
        )

    return query

def find_contract_metadata(search_for, case_statements, filter_or, filter_and, archived=False):
    '''
    Takes a search term, case statements, and filter clauses and
    returns out a list of search results objects to be rendered into
    the template.

    Arguments:
        search_for: User's search term
        case_statements: An iterable of `Sqlalchemy case expressions`_
        filter_or: An iterable of `Sqlalchemy query filters`_, used for non-exclusionary filtering
        filter_and: An iterable of `Sqlalchemy query filters`_, used for exclusionary filtering
        archived: Boolean of whether or not to add the ``is_archived`` filter

    Returns:
        A Sqlalchemy resultset that contains the fields to render the
        search results view.
    '''

    rank = db.func.max(db.func.full_text.ts_rank(
        db.func.setweight(db.func.coalesce(SearchView.tsv_company_name, ''), 'A').concat(
            db.func.setweight(db.func.coalesce(SearchView.tsv_contract_description, ''), 'A')
        ).concat(
            db.func.setweight(db.func.coalesce(SearchView.tsv_detail_value, ''), 'D')
        ).concat(
            db.func.setweight(db.func.coalesce(SearchView.tsv_line_item_description, ''), 'B')
        ), db.func.to_tsquery(search_for, postgresql_regconfig='english')
    ))

    contracts = db.session.query(
        db.distinct(SearchView.contract_id).label('contract_id'),
        SearchView.company_id, SearchView.contract_description,
        SearchView.financial_id, SearchView.expiration_date,
        SearchView.company_name, db.case(case_statements).label('found_in'),
        rank.label('rank')
    ).join(
        ContractBase, ContractBase.id == SearchView.contract_id
    ).filter(
        db.or_(
            db.cast(SearchView.financial_id, db.String) == search_for,
            *filter_or
        ),
        *filter_and
    ).group_by(
        SearchView.contract_id,
        SearchView.company_id,
        SearchView.contract_description,
        SearchView.financial_id,
        SearchView.expiration_date,
        SearchView.company_name,
        db.case(case_statements)
    ).order_by(
        db.text('rank DESC')
    )

    contracts = add_archived_filter(contracts, archived)

    return contracts.all()

def return_all_contracts(filter_and, archived=False):
    '''Return all contracts in the event of an empty search

    Arguments:
        filter_and: An iterable of `Sqlalchemy query filters`_, used for exclusionary filtering
        archived: Boolean of whether or not to add the ``is_archived`` filter

    Returns:
        A Sqlalchemy resultset that contains the fields to render the
        search results view.
    '''
    contracts = db.session.query(
        db.distinct(SearchView.contract_id).label('contract_id'), SearchView.company_id,
        SearchView.contract_description, SearchView.financial_id,
        SearchView.expiration_date, SearchView.company_name
    ).join(ContractBase, ContractBase.id == SearchView.contract_id).filter(
        *filter_and
    )

    contracts = add_archived_filter(contracts, archived)

    return contracts.all()
