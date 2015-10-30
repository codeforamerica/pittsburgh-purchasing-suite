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
from purchasing.notifications import Notification

from purchasing.scout.forms import SearchForm, FeedbackForm, NoteForm
from purchasing.users.models import Department, User, Role
from purchasing.data.searches import SearchView, find_contract_metadata, return_all_contracts
from purchasing.data.companies import Company
from purchasing.data.contracts import ContractBase, ContractNote, ContractType

from purchasing.scout import blueprint

CRAZY_CHARS = re.compile('[^A-Za-z0-9 ]')

@blueprint.route('/', methods=['GET'])
@wrap_form(SearchForm, 'search_form', 'scout/explore.html')
def explore():
    '''
    The landing page for scout. Renders the "big search"
    template.
    '''
    return dict(current_user=current_user, choices=Department.choices())

@blueprint.route('/filter', methods=['GET'])
def filter_no_department():
    '''The landing page for filtering by departments
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
    '''
    Filter contracts by which ones have departmental subscribers
    '''
    pagination_per_page = current_app.config.get('PER_PAGE', 50)
    page = int(request.args.get('page', 1))
    lower_bound_result = (page - 1) * pagination_per_page
    upper_bound_result = lower_bound_result + pagination_per_page
    department = Department.query.get(int(department_id))

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

def build_filter(req_args, fields, search_for, filter_form, _all):
    '''Build the where clause filter
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
    '''Build the case when statements
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

@blueprint.route('/search', methods=['GET', 'POST'])
def search():
    '''
    The search results page for scout
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

    # build filter and filter form
    fields = [
        ('company_name', 'Company Name', SearchView.tsv_company_name),
        ('line_item', 'Line Item', SearchView.tsv_line_item_description),
        ('contract_description', 'Contract Description', SearchView.tsv_contract_description),
        ('contract_detail', 'Contract Detail', SearchView.tsv_detail_value),
        ('financial_id', 'Controller Number', SearchView.financial_id),
    ]

    filter_or = build_filter(
        request.args, fields, search_for, search_form,
        not any([request.args.get(name) for name, _, _ in fields])
    )

    filter_and = []
    if request.args.get('contract_type') is not None:
        filter_and = [
            ContractBase.contract_type_id == int(request.args.get('contract_type'))
        ]
        search_form.contract_type.data = ContractType.query.get(int(request.args.get('contract_type')))

    found_in_case = build_cases(
        request.args, fields, search_for,
        not any([request.args.get(name) for name, _, _ in fields])
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

def feedback_handler(contract_id=None, search_for=None):
    '''
    Allow user to send feedback on the data present in a specific contract
    '''
    if contract_id:
        contract = ContractBase.query.get(contract_id)
    else:
        contract = ContractBase(
            description='Search term: ' + search_for
        )

    search_form = SearchForm()
    if contract:
        form = FeedbackForm()

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
    abort(404)

@blueprint.route('/contracts/feedback/<search_for>', methods=['GET', 'POST'])
def search_feedback(search_for):
    return feedback_handler(search_for=search_for)

@blueprint.route('/contracts/<int:contract_id>/feedback', methods=['GET', 'POST'])
def feedback(contract_id):
    return feedback_handler(contract_id=contract_id)

@blueprint.route('/contracts/<int:contract_id>/subscribe')
@requires_roles('staff', 'admin', 'superadmin', 'conductor')
def subscribe(contract_id):
    '''Subscribes a user to receive updates about a particular contract
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
