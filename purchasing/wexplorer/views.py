# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, current_app,
    request, abort, flash, redirect
)
from flask_login import current_user

from purchasing.database import db
from purchasing.utils import SimplePagination
from purchasing.decorators import wrap_form, requires_roles
from purchasing.wexplorer.forms import SearchForm
from purchasing.data.companies import get_one_company
from purchasing.data.contracts import (
    get_one_contract, follow_a_contract, unfollow_a_contract
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
    return dict(current_user=current_user)

@blueprint.route('/search', methods=['GET'])
def search():
    '''
    The search results page for wexplorer. Renders the "side search"
    along with paginated results.
    '''
    search_form = SearchForm(request.form)
    pagination_per_page = current_app.config.get('PER_PAGE', 50)

    results = []
    search_for = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    lower_bound_result = (page - 1) * pagination_per_page
    upper_bound_result = lower_bound_result + pagination_per_page

    # TODO: Make this more efficient. Maybe break it into multiple
    # queries and them join those together in the python?
    contracts = db.session.execute(
        '''
        SELECT
            x.company_id, x.contract_id,
            x.company_name, x.description,
            array_agg(u.email)
        FROM (
            SELECT
                cp.id as company_id, ct.id as contract_id,
                cp.company_name, ct.description
            FROM company cp
            FULL OUTER JOIN company_contract_association cca
            ON cp.id = cca.company_id
            FULL OUTER JOIN contract ct
            ON ct.id = cca.contract_id
            WHERE cp.company_name ilike :search_for_wc
            OR ct.description ilike :search_for_wc
        ) x
        FULL OUTER JOIN
        contract_user_association cca
        ON x.contract_id = cca.contract_id
        LEFT OUTER JOIN
        users u
        ON cca.user_id = u.id
        group by 1,2,3,4
        ''',
        {
            'search_for_wc': '%' + str(search_for) + '%'
        }
    ).fetchall()

    pagination = SimplePagination(page, pagination_per_page, len(contracts))

    for contract in contracts[lower_bound_result:upper_bound_result]:
        results.append({
            'company_id': contract[0],
            'contract_id': contract[1],
            'company_name': contract[2],
            'contract_description': contract[3],
            'users': contract[4]
        })

    return render_template(
        'wexplorer/search.html',
        results=results,
        pagination=pagination,
        search_form=search_form,
        path='{path}?{query}'.format(
            path=request.path, query=request.query_string
        )
    )

@blueprint.route('/companies/<int:company_id>')
@wrap_form(SearchForm, 'search_form', 'wexplorer/company.html')
def company(company_id):
    company = get_one_company(company_id)
    if company:
        return dict(
            company=company,
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
        return dict(
            contract=contract,
            path='{path}?{query}'.format(
                path=request.path, query=request.query_string
            )
        )
    abort(404)

@blueprint.route('/contracts/<int:contract_id>/subscribe')
@requires_roles('staff', 'admin', 'superadmin')
def subscribe(contract_id):
    '''
    Subscribes a user to receive updates about a particular contract
    '''
    message, contract = follow_a_contract(contract_id, current_user)
    next_url = request.args.get('next', '/wexplorer')
    if contract:
        flash(message[0], message[1])
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
    message, contract = unfollow_a_contract(contract_id, current_user)
    next_url = request.args.get('next', '/wexplorer')
    if contract:
        flash(message[0], message[1])
        return redirect(next_url)
    elif contract is None:
        abort(404)
    abort(403)
