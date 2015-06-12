# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, current_app,
    request, abort, flash, redirect, url_for
)
from flask_login import current_user

from purchasing.database import db
from purchasing.utils import SimplePagination
from purchasing.decorators import wrap_form, requires_roles
from purchasing.notifications import wexplorer_feedback
from purchasing.wexplorer.forms import SearchForm, FeedbackForm, FilterForm
from purchasing.data.models import (
    ContractBase, contract_user_association_table, contract_starred_association_table
)
from purchasing.users.models import DEPARTMENT_CHOICES
from purchasing.data.companies import get_one_company
from purchasing.data.contracts import (
    get_one_contract, follow_a_contract, unfollow_a_contract, get_all_contracts
)

blueprint = Blueprint(
    'wexplorer', __name__, url_prefix='/wexplorer',
    template_folder='../templates'
)

@blueprint.route('/', methods=['GET'])
@wrap_form(SearchForm, 'search_form', 'wexplorer/explore.html')
def explore():
    '''
    The landing page for wexplorer. Renders the "big search"
    template.
    '''
    return dict(current_user=current_user, choices=DEPARTMENT_CHOICES[1:])

@blueprint.route('/filter', methods=['GET'])
@blueprint.route('/filter/<department>', methods=['GET'])
def filter(department=None):
    '''
    Filter contracts by which ones have departmental subscribers
    '''
    pagination_per_page = current_app.config.get('PER_PAGE', 50)
    page = int(request.args.get('page', 1))
    lower_bound_result = (page - 1) * pagination_per_page
    upper_bound_result = lower_bound_result + pagination_per_page

    if department not in [i[0] for i in DEPARTMENT_CHOICES]:
        flash('You must choose a valid department!', 'alert-danger')
        return redirect(url_for('wexplorer.explore'))

    contracts = db.session.query(
        ContractBase.id, ContractBase.description,
        db.func.count(contract_user_association_table.c.user_id).label('cnt'),
        db.func.count(contract_starred_association_table.c.user_id).label('cnt2')
    ).outerjoin(contract_user_association_table).outerjoin(
        contract_starred_association_table
    ).filter(db.or_(
        ContractBase.users.any(department=department),
        ContractBase.starred.any(department=department)
    )).group_by(ContractBase).having(db.or_(
        db.func.count(contract_user_association_table.c.user_id) > 0,
        db.func.count(contract_starred_association_table.c.user_id) > 0
    )).order_by('cnt DESC').all()

    pagination = SimplePagination(page, pagination_per_page, len(contracts))

    results = contracts[lower_bound_result:upper_bound_result]

    current_app.logger.info('WEXFILTER - {department}: Filter by {department}'.format(department=department))

    return render_template(
        'wexplorer/filter.html',
        search_form=SearchForm(),
        results=results,
        pagination=pagination,
        department=department,
        choices=DEPARTMENT_CHOICES[1:],
        path='{path}?{query}'.format(
            path=request.path, query=request.query_string
        )
    )

def build_filter(req_args, fields, filter_form, _all):
    '''Build the where clause filter
    '''
    clauses = []
    for arg_name, filter_field, _filter in fields:
        if _all or req_args.get(arg_name) == 'y':
            if not _all:
                filter_form[arg_name].checked = True
            clauses.append('{} {} :search_for'.format(filter_field, _filter))
    return 'WHERE ' + ' OR '.join(clauses)

@blueprint.route('/search', methods=['GET'])
def search():
    '''
    The search results page for wexplorer. Renders the "side search"
    along with paginated results.
    '''
    department = request.args.get('department')
    if department and department not in ['', 'None']:
        return redirect(url_for('wexplorer.filter', department=department))

    search_form = SearchForm(request.form)
    search_for = request.args.get('q', '')
    results = []

    pagination_per_page = current_app.config.get('PER_PAGE', 50)
    page = int(request.args.get('page', 1))
    lower_bound_result = (page - 1) * pagination_per_page
    upper_bound_result = lower_bound_result + pagination_per_page

    # build filter and filter form
    filter_form = FilterForm()
    fields = [
        ('company_name', 'cp.company_name', '~*'),
        ('contract_description', 'ct.description', '~*'),
        ('contract_detail', 'ctp.value', '~*'),
        ('line_item', 'li.description', '~*'),
        ('financial_id', 'ct.financial_id::VARCHAR', '=')
    ]

    filter_where = build_filter(
        request.args, fields, filter_form,
        not any([request.args.get(name) for name, search_clause, _filter in fields])
    )

    # TODO: Make this more efficient. Maybe break it into multiple
    # queries and them join those together in the python?
    contracts = db.session.execute(
        '''
        SELECT
            x.company_id, x.contract_id,
            x.company_name, x.description,
            x.expiration_date, x.financial_id,
            x.found_in, array_agg(u.email)
        FROM (
            SELECT
                cp.id as company_id, ct.id as contract_id,
                cp.company_name, ct.description,
                ct.expiration_date, ct.financial_id,
                CASE
                  WHEN cp.company_name ~* :search_for then 'Company Name'
                  WHEN ct.description ~* :search_for then 'Contract Description'
                  WHEN ctp.value ~* :search_for then 'Contract Detail'
                  WHEN li.description ~* :search_for then 'Line Item'
                  WHEN ct.financial_id::VARCHAR = :search_for then 'Financial ID (Controller Number)'
                  ELSE NULL
                END as found_in
            FROM company cp
            FULL OUTER JOIN company_contract_association cca
            ON cp.id = cca.company_id
            FULL OUTER JOIN contract ct
            ON ct.id = cca.contract_id
            LEFT JOIN contract_property ctp
            ON ct.id = ctp.contract_id
            LEFT JOIN line_item li
            ON ct.id = li.contract_id
            {filter_where}
        ) x
        FULL OUTER JOIN
        contract_user_association cca
        ON x.contract_id = cca.contract_id
        LEFT OUTER JOIN
        users u
        ON cca.user_id = u.id
        WHERE x.contract_id IS NOT NULL
        group by 1,2,3,4,5,6,7
        '''.format(
            filter_where=filter_where
        ),
        {
            'search_for': str(search_for)
        }
    ).fetchall()

    for contract in contracts[lower_bound_result:upper_bound_result]:
        results.append({
            'company_id': contract[0],
            'contract_id': contract[1],
            'company_name': contract[2],
            'contract_description': contract[3],
            'expiration_date': contract[4],
            'financial_id': contract[5],
            'found_in': contract[6],
            'users': contract[7],
        })

    pagination = SimplePagination(page, pagination_per_page, len(contracts))

    current_app.logger.info('WEXSEARCH - {search_for}: {user} searched for "{search_for}"'.format(
        search_for=search_for,
        user=current_user.email if not current_user.is_anonymous() else 'anonymous'
    ))

    user_starred = [] if current_user.is_anonymous() else current_user.get_starred()

    return render_template(
        'wexplorer/search.html',
        current_user=current_user,
        filter_form=filter_form,
        user_starred=user_starred,
        search_for=search_for,
        results=results,
        pagination=pagination,
        search_form=search_form,
        choices=DEPARTMENT_CHOICES[1:],
        path='{path}?{query}'.format(
            path=request.path, query=request.query_string
        )
    )

@blueprint.route('/companies/<int:company_id>')
@wrap_form(SearchForm, 'search_form', 'wexplorer/company.html')
def company(company_id):
    company = get_one_company(company_id)

    if company:
        current_app.logger.info('WEXCOMPANY - Viewed company page {}'.format(company.company_name))
        return dict(
            company=company,
            choices=DEPARTMENT_CHOICES[1:],
            path='{path}?{query}'.format(
                path=request.path, query=request.query_string
            )
        )
    abort(404)

@blueprint.route('/contracts/<int:contract_id>')
@wrap_form(SearchForm, 'search_form', 'wexplorer/contract.html')
def contract(contract_id):
    contract = get_one_contract(contract_id)

    if contract:

        current_app.logger.info('WEXCONTRACT - Viewed contract page {}'.format(contract.description))

        departments = set([i.department for i in contract.users])

        return dict(
            contract=contract,
            departments=departments,
            choices=DEPARTMENT_CHOICES[1:],
            path='{path}?{query}'.format(
                path=request.path, query=request.query_string
            )
        )
    abort(404)

@blueprint.route('/contracts/<int:contract_id>/feedback', methods=['GET', 'POST'])
def feedback(contract_id):
    '''
    Allow user to send feedback on the data present in a specific contract
    '''
    contract = get_one_contract(contract_id)
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

            feedback_sent = wexplorer_feedback(
                contract, form.data.get('sender'), form.data.get('body')
            )

            if feedback_sent:
                flash('Thank you for your feedback!', 'alert-success')
            else:
                flash('Oh no! Something went wrong. We are looking into it.', 'alert-danger')

            return redirect(url_for('wexplorer.contract', contract_id=contract.id))

        return render_template(
            'wexplorer/feedback.html',
            search_form=search_form,
            contract=contract,
            choices=DEPARTMENT_CHOICES[1:],
            feedback_form=form
        )
    abort(404)

@blueprint.route('/contracts/<int:contract_id>/star')
@requires_roles('staff', 'admin', 'superadmin')
def star(contract_id):
    '''

    '''
    message, contract = follow_a_contract(contract_id, current_user, 'star')
    next_url = request.args.get('next', '/wexplorer')
    if contract:
        flash(message[0], message[1])

        'STAR: {user} starred {contract}'.format(user=current_user.email, contract=contract_id)
        return redirect(next_url)
    elif contract is None:
        abort(404)
    abort(403)

@blueprint.route('/contracts/<int:contract_id>/unstar')
@requires_roles('staff', 'admin', 'superadmin')
def unstar(contract_id):
    '''

    '''
    message, contract = unfollow_a_contract(contract_id, current_user, 'star')
    next_url = request.args.get('next', '/wexplorer')
    if contract:
        flash(message[0], message[1])

        'STAR: {user} starred {contract}'.format(user=current_user.email, contract=contract_id)
        return redirect(next_url)
    elif contract is None:
        abort(404)
    abort(403)

@blueprint.route('/contracts/<int:contract_id>/subscribe')
@requires_roles('staff', 'admin', 'superadmin')
def subscribe(contract_id):
    '''
    Subscribes a user to receive updates about a particular contract
    '''
    message, contract = follow_a_contract(contract_id, current_user, 'follow')
    next_url = request.args.get('next', '/wexplorer')
    if contract:
        flash(message[0], message[1])

        'SUBSCRIBE: {user} subscribed to {contract}'.format(user=current_user.email, contract=contract_id)
        return redirect(next_url)
    elif contract is None:
        abort(404)
    abort(403)

@blueprint.route('/contracts/<int:contract_id>/unsubscribe')
@requires_roles('staff', 'admin', 'superadmin')
def unsubscribe(contract_id):
    '''
    Unsubscribes a user from receiving updates about a particular contract
    '''
    message, contract = unfollow_a_contract(contract_id, current_user, 'follow')
    next_url = request.args.get('next', '/wexplorer')
    if contract:
        flash(message[0], message[1])

        'UNSUBSCRIBE: {user} unsubscribed from {contract}'.format(user=current_user.email, contract=contract_id)
        return redirect(next_url)
    elif contract is None:
        abort(404)
    abort(403)
