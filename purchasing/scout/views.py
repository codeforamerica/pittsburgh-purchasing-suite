# -*- coding: utf-8 -*-

import re

from flask import (
    render_template, current_app,
    request, abort, flash, redirect, url_for
)
from flask_login import current_user

from purchasing.database import db
from purchasing.utils import SimplePagination
from purchasing.decorators import wrap_form, requires_roles

from purchasing.scout.forms import SearchForm, NoteForm
from purchasing.users.models import Department
from purchasing.data.companies import Company
from purchasing.data.contracts import ContractBase, ContractNote, ContractType

from purchasing.scout.util import (
    build_filter, build_cases, feedback_handler,
    find_contract_metadata, return_all_contracts, FILTER_FIELDS
)

from purchasing.scout import blueprint

CRAZY_CHARS = re.compile('[^A-Za-z0-9 ]')

@blueprint.route('/', methods=['GET'])
@wrap_form(SearchForm, 'search_form', 'scout/explore.html')
def explore():
    '''The landing page for scout. Renders the "big search" template.

    :status 200: Renders the appropriate landing page.
    '''
    return dict(current_user=current_user, choices=Department.choices())

@blueprint.route('/filter', methods=['GET'])
def filter_no_department():
    '''The landing page for filtering by departments

    :status 200: Renders the appropriate landing page.
    '''
    return render_template(
        'scout/filter.html',
        search_form=SearchForm(),
        results=[],
        choices=Department.choices(),
        path='{path}?{query}'.format(
            path=request.path, query=request.query_string
        )
    )

@blueprint.route('/filter/<int:department_id>', methods=['GET'])
def filter(department_id):
    '''Filter contracts by which ones have departmental subscribers

    :param department_id: Department's unique ID
    :status 200: Renders template with all contracts followed by that department
    :status 404: When department is not found with the specified ID
    '''
    department = Department.query.get(int(department_id))

    if department:
        pagination_per_page = current_app.config.get('PER_PAGE', 50)
        page = int(request.args.get('page', 1))
        lower_bound_result = (page - 1) * pagination_per_page
        upper_bound_result = lower_bound_result + pagination_per_page

        contracts = db.session.execute(
            '''
            SELECT
                contract.id, description,
                count(contract_user_association.user_id) AS follows
            FROM contract
            LEFT OUTER JOIN contract_user_association
                ON contract.id = contract_user_association.contract_id
            FULL OUTER JOIN users
                ON contract_user_association.user_id = users.id
            JOIN department
                ON users.department_id = department.id
            WHERE department.id = :department
            GROUP BY 1,2
            HAVING count(contract_user_association.user_id) > 0
            ORDER BY 3 DESC, 1 ASC
            ''', {'department': int(department_id)}
        ).fetchall()

        if len(contracts) > 0:
            pagination = SimplePagination(page, pagination_per_page, len(contracts))
            results = contracts[lower_bound_result:upper_bound_result]
        else:
            pagination = None
            results = []

        current_app.logger.info('WEXFILTER - {department}: Filter by {department}'.format(
            department=department.name
        ))

        return render_template(
            'scout/filter.html',
            search_form=SearchForm(),
            results=results,
            pagination=pagination,
            department=department,
            choices=Department.choices(),
            path='{path}?{query}'.format(
                path=request.path, query=request.query_string
            )
        )
    abort(404)

@blueprint.route('/search', methods=['GET', 'POST'])
def search():
    '''The search results page for scout

    In order to create permalinks to each search/filter result combination,
    POST methods have their form arguments popped off and then are immediately
    redirected to GET methods.

    .. seealso ::
        * :py:mod:`purchasing.data.searches` for more on the search query
        * :py:class:`purchasing.scout.forms.SearchForm` for the search form construction
        * :py:func:`purchasing.scout.util.build_filter` for how filters are built
        * :py:func:`purchasing.scout.util.build_cases` for how case statements are built
    '''
    if request.method == 'POST':
        args = request.form.to_dict()
        if args.get('contract_type') == '__None':
            del args['contract_type']

        return redirect(url_for('scout.search', **args))

    department = request.args.get('department')
    if department and department not in ['', 'None']:
        return redirect(url_for('scout.filter', department=department))

    search_form = SearchForm()
    search_for = request.args.get('q') or ''
    search_form.q.data = search_for

    # strip out "crazy" characters
    search_for = re.sub(CRAZY_CHARS, '', search_for)
    search_for = ' | '.join(search_for.split())

    pagination_per_page = current_app.config.get('PER_PAGE', 50)
    page = int(request.args.get('page', 1))
    lower_bound_result = (page - 1) * pagination_per_page
    upper_bound_result = lower_bound_result + pagination_per_page

    filter_or = build_filter(
        request.args, FILTER_FIELDS, search_for, search_form,
        not any([request.args.get(name) for name, _, _ in FILTER_FIELDS])
    )

    filter_and = []
    if request.args.get('contract_type') is not None:
        filter_and = [
            ContractBase.contract_type_id == int(request.args.get('contract_type'))
        ]
        search_form.contract_type.data = ContractType.query.get(int(request.args.get('contract_type')))

    found_in_case = build_cases(
        request.args, FILTER_FIELDS, search_for,
        not any([request.args.get(name) for name, _, _ in FILTER_FIELDS])
    )

    # determine if we are getting archived contracts
    if request.args.get('archived') == 'y':
        search_form['archived'].checked = True
        archived = True
    else:
        archived = False

    if search_for != '':
        contracts = find_contract_metadata(
            search_for, found_in_case, filter_or, filter_and,
            archived
        )
    else:
        contracts = return_all_contracts(
            filter_and, archived
        )

    pagination = SimplePagination(page, pagination_per_page, len(contracts))

    current_app.logger.info('WEXSEARCH - {search_for}: {user} searched for "{search_for}"'.format(
        search_for=search_for,
        user=current_user.email if not current_user.is_anonymous() else 'anonymous'
    ))

    user_follows = [] if current_user.is_anonymous() else current_user.get_following()

    return render_template(
        'scout/search.html',
        current_user=current_user,
        user_follows=user_follows,
        search_for=search_for,
        results=contracts[lower_bound_result:upper_bound_result],
        pagination=pagination,
        search_form=search_form,
        choices=Department.choices(),
        path='{path}?{query}'.format(
            path=request.path, query=request.query_string
        )
    )

@blueprint.route('/companies/<int:company_id>')
@wrap_form(SearchForm, 'search_form', 'scout/company.html')
def company(company_id):
    '''Company profile page

    :param contract_id: Unique ID for a :py:class:`purchasing.data.company.Company` object
    :status 200: Renders the company profile template
    :status 404: Unique company ID not found
    '''
    company = Company.query.get(company_id)

    if company:
        current_app.logger.info('WEXCOMPANY - Viewed company page {}'.format(company.company_name))
        return dict(
            company=company,
            choices=Department.choices(),
            path='{path}?{query}'.format(
                path=request.path, query=request.query_string
            )
        )
    abort(404)

@blueprint.route('/contracts/<int:contract_id>', methods=['GET', 'POST'])
@wrap_form(SearchForm, 'search_form', 'scout/contract.html')
def contract(contract_id):
    '''Contract profile page

    For GET requests, render the profile page. For POSTs,
    try to submit a new note.

    :param contract_id: Unique ID for a :py:class:`purchasing.data.contracts.ContractBase` object
    :status 200: Renders the contract profile template
    :status 302: Try to post note, then redirect to the same page's contract view
    :status 404: Unique contract ID not found
    '''

    contract = ContractBase.query.get(contract_id)

    if contract:
        note_form = NoteForm()

        if note_form.validate_on_submit():
            new_note = ContractNote(
                note=note_form.data['note'],
                contract_id=contract_id, taken_by_id=current_user.id
            )
            db.session.add(new_note)
            db.session.commit()
            return redirect(url_for('scout.contract', contract_id=contract_id))

        notes = ContractNote.query.filter(
            ContractNote.contract_id == contract_id,
            ContractNote.taken_by_id == current_user.id
        ).all()

        departments = set([i.department for i in contract.followers])

        current_app.logger.info('WEXCONTRACT - Viewed contract page {}'.format(contract.description))

        return dict(
            contract=contract, departments=departments,
            choices=Department.choices(),
            path='{path}?{query}'.format(
                path=request.path, query=request.query_string
            ), notes=notes, note_form=note_form
        )
    abort(404)

@blueprint.route('/contracts/feedback/<search_for>', methods=['GET', 'POST'])
def search_feedback(search_for):
    '''Provide feedback about an empty search

    This page is only viewable in the event of a search that returns 0 results.

    :param search_for: Search term.

    .. seealso ::
        :py:mod:`purchasing.scout.util.feedback_handler` for information on how
        the feedback is processed and handled
    '''
    contract = ContractBase(description='Search term: ' + search_for)
    return feedback_handler(contract, search_for=search_for)

@blueprint.route('/contracts/<int:contract_id>/feedback', methods=['GET', 'POST'])
def feedback(contract_id):
    '''Provide feedback about a contract

    :param contract_id: Unique ID for a :py:class:`purchasing.data.contracts.ContractBase` object

    .. seealso ::
        :py:mod:`purchasing.scout.util.feedback_handler` for information on how
        the feedback is processed and handled
    '''
    contract = ContractBase.query.get(contract_id)
    if contract:
        return feedback_handler(contract=contract)
    abort(404)

@blueprint.route('/contracts/<int:contract_id>/subscribe')
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def subscribe(contract_id):
    '''Subscribes a user to receive updates about a particular contract

    :param contract_id: Unique ID for a :py:class:`purchasing.data.contracts.ContractBase` object
    '''
    contract = ContractBase.query.get(contract_id)
    next_url = request.args.get('next', '/scout')

    if contract:
        message = contract.add_follower(current_user)
        db.session.commit()
        flash(message[0], message[1])

        current_app.logger.info(
            'SUBSCRIBE: {user} subscribed to {contract}'.format(
                user=current_user.email, contract=contract_id
            )
        )

        return redirect(next_url)

    elif contract is None:
        db.session.rollback()
        abort(404)

    abort(403)

@blueprint.route('/contracts/<int:contract_id>/unsubscribe')
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def unsubscribe(contract_id):
    '''Unsubscribes a user from receiving updates about a particular contract

    :param contract_id: Unique ID for a :py:class:`purchasing.data.contracts.ContractBase` object
    '''
    contract = ContractBase.query.get(contract_id)
    next_url = request.args.get('next', '/scout')

    if contract:
        message = contract.remove_follower(current_user)
        db.session.commit()
        flash(message[0], message[1])

        current_app.logger.info(
            'UNSUBSCRIBE: {user} unsubscribed from {contract}'.format(
                user=current_user.email, contract=contract_id
            )
        )

        return redirect(next_url)

    elif contract is None:
        db.session.rollback()
        abort(404)

    abort(403)
