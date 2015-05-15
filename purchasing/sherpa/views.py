# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, url_for
)
from purchasing.extensions import login_manager
from purchasing.users.models import User

blueprint = Blueprint(
    'sherpa', __name__, url_prefix='/sherpa',
    static_folder='../static', template_folder='../templates'
)

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

@blueprint.route("/", methods=["GET", "POST"])
def index():
    '''
    Landing page for sherpa
    '''
    title = "Explore the Pittsburgh Procurement Process!"
    pre_button_content = [{
        'title': 'What are you doing?',
        'content': '''
            Need to start a contract or wondering which process you should use to buy \
            something? Get started by selecting an option below!
        '''
    }]
    buttons = [{
        'url': url_for('sherpa.index'),
        'text': 'Start a contract!'
    }, {
        'url': url_for('sherpa.buy_something'),
        'text': 'Buy something!'
    }]

    return render_template(
        "sherpa/index.html",
        title=title,
        pre_button_content=pre_button_content,
        buttons=buttons,
    )

@blueprint.route("/is-it-on-contract", methods=["GET", "POST"])
def buy_something():
    '''
    First question for the buy something flow
    '''
    title = "Is it on contract?"
    buttons = [{
        'url': url_for('sherpa.use_it'),
        'text': 'Yes'
    }, {
        'url': url_for('sherpa.sourcing'),
        'text': 'No'
    }, {
        'url': '../wexplorer',
        'text': "I don't know"
    }]
    prev = {
        'url': url_for('sherpa.index'),
        'text': 'Getting started'
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/use-it", methods=["GET", "POST"])
def use_it():
    '''
    For those who don't really need to use this app
    '''
    title = "Buy or use it!"
    prev = {
        'url': url_for('sherpa.index'),
        'text': 'Getting started'
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev
    )

@blueprint.route("/what-are-you-sourcing", methods=["GET", "POST"])
def sourcing():
    '''
    Second question for the buy something flow
    '''
    title = "What are you sourcing?"
    buttons = [{
        'url': url_for('sherpa.emergency_prof_services'),
        'text': 'Professional Services'
    }, {
        'url': url_for('sherpa.goods_services'),
        'text': 'Goods/Services'
    }, {
        'url': url_for('sherpa.construction'),
        'text': "Construction"
    }]
    prev = {
        'url': url_for('sherpa.buy_something'),
        'text': 'Is it on contract?'
    }
    content = '''
        <h4>What's the difference between professional services and goods/services?</h4>
        <p>
          Good question! The following definition of professional services is excerpted from a City of Pittsburgh 2009 policy memo about such services:
        </p>
        <blockquote>
          <p>
            <strong>Professional Services contract</strong> - a contract involving services of members of the medical or legal profession, registered architects, appraisers, auditors, engineers, certified public accountants or other personal services that involve quality as the paramount concern and require a recognized professional and special expertise.
          </p>
        </blockquote>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev,
        content=content
    )

@blueprint.route("/construction", methods=["GET", "POST"])
def construction():
    '''
    End of the construction flow
    '''
    title = "Use the construction process."
    prev = {
        'url': url_for('sherpa.sourcing'),
        'text': "What are you sourcing?"
    }
    content = '<p>More information about the construction process coming soon!</p>'

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )

@blueprint.route("/emergency-professional-services", methods=["GET", "POST"])
def emergency_prof_services():
    '''
    First question for professional services sub-flow
    '''
    title = "Is it an emergency?"
    buttons = [{
        'url': url_for('sherpa.wallace_prof'),
        'text': 'Yes'
    }, {
        'url': url_for('sherpa.sole_source'),
        'text': 'No'
    }]
    prev = {
        'url': url_for('sherpa.sourcing'),
        'text': 'What are you sourcing?'
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/wallace-act-professional-service", methods=["GET", "POST"])
def wallace_prof():
    '''
    End of emergency professional services flow
    '''
    title = "Use the Wallace Act Process"
    prev = {
        'url': url_for('sherpa.emergency_prof_services'),
        'text': 'Is it an emergency?'
    }
    content = '''
        <p>
          The Wallace Act covers the emergency purchase of goods and services not on a contract whose costs exceed $2,000. These purchases will require City Council approval after the fact.
        </p>
        <p>
          More information about the Wallace Act is coming soon.
        </p>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )

@blueprint.route("/is-it-sole-sourced", methods=["GET", "POST"])
def sole_source():
    '''
    First question for professional services sub-flow
    '''
    title = "Is there only one supplier (sole sourced)?"
    buttons = [{
        'url': url_for('sherpa.sole_rfp'),
        'text': 'Yes'
    }, {
        'url': url_for('sherpa.dept_rfp'),
        'text': 'No'
    }]
    prev = {
        'url': url_for('sherpa.emergency_prof_services'),
        'text': 'Is it an emergency?'
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/sole-source-department-rfp", methods=["GET", "POST"])
def sole_rfp():
    '''
    End of sole source professional services flow
    '''
    title = "Write a sole source RFP"
    prev = {
        'url': url_for('sherpa.sole_source'),
        'text': 'Is there only one supplier?'
    }
    content = '''
        <p>Sole source agreements are unique professional service agreements which may include
        subscriptions, sometimes include maintenance/warranty work on equipment.</p>
        <p>According to a 2009 City of Pittsburgh policy document,</p>

        <blockquote><p>
          a <strong>Sole Source Professional Services contract</strong> is a contract
          involving unique professional services that are documented to be "available from one source only. An example could
          be art restoration by a particular artist on his or her own work. The term may also
          include specialized training or maintenance services on verified sole-source purchases.
        </p></blockquote>

        <p>More information about sole source contracts is coming soon.</p>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )

@blueprint.route("/department-rfp", methods=["GET", "POST"])
def dept_rfp():
    '''
    End of competitive bid professional services flow
    '''
    title = "Write and issue a department RFP"
    prev = {
        'url': url_for('sherpa.sole_source'),
        'text': 'Is there only one supplier?'
    }
    content = '''
        <p>More information about RFPs and the RFP writing process is coming soon. For some
        reference materials, take a look at the list of currently open contract bids in the
        following places: </p>
        <ul>
          <li><a href="http://pittsburghpa.gov/omb/contract-bids"> Office of Management and Budget</a></li>
          <li><a href="http://pittsburghpa.gov/dcp/rfp-rfq">Department of City Planning</a></li>
          <li><a href="http://www.pgh2o.com/doing-business">Pittsburgh Water and Sewer Authority</a></li>
          <li><a href="http://www.ura.org/working_with_us/proposals.php">Urban Redevelopment Authority of Pittsburgh</a></li>
        </ul>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )

@blueprint.route("/goods-services", methods=["GET", "POST"])
def goods_services():
    '''
    First question for goods/services flow
    '''
    title = "Is the item's cost under $2,000?"
    buttons = [{
        'url': url_for('sherpa.explanatory'),
        'text': 'Yes'
    }, {
        'url': url_for('sherpa.emergency_goods'),
        'text': 'No'
    }]
    prev = {
        'url': url_for('sherpa.sourcing'),
        'text': 'What are you sourcing?'
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/explanatory", methods=["GET", "POST"])
def explanatory():
    '''
    End of the explanatory process flow
    '''
    title = "Use the Explanatory Process"
    prev = {
        'url': url_for('sherpa.goods_services'),
        'text': "Is the item's cost under $2000?"
    }
    content = '''
        <p>The Explanatory Process allows you to purchase an item whose total cost is
        $2,000 or less without a contract. However, this purchase must receive
        <em>pre-approval</em> from both the Director of your department and the Director
        of the Office of Management and Budget, and final approval from City Council.</p>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )


@blueprint.route("/emergency-goods", methods=["GET", "POST"])
def emergency_goods():
    '''
    Followup for goods/services flow
    '''
    title = "Is it an emergency purchase?"
    buttons = [{
        'url': url_for('sherpa.wallace_goods'),
        'text': 'Yes'
    }, {
        'url': url_for('sherpa.thirty_thousand'),
        'text': 'No'
    }]
    prev = {
        'url': url_for('sherpa.goods_services'),
        'text': "Is the item's cost under $2,000?"
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/wallace-act-goods", methods=["GET", "POST"])
def wallace_goods():
    '''
    End of emergency goods flow
    '''
    title = "Use the Wallace Act Process"
    prev = {
        'url': url_for('sherpa.emergency_goods'),
        'text': 'Is it an emergency?'
    }
    content = '''
        <p>The Wallace Act covers the emergency purchase of goods and services not on a contract
        whose costs exceed $2,000. These purchases will require City Council approval after
        the fact.</p>
        <p>More information about the Wallace Act is coming soon.</p>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )

@blueprint.route("/over-30-thousand", methods=["GET", "POST"])
def thirty_thousand():
    '''
    Followup for non emergency purchases more than $2000
    '''
    title = "Is the items cost over $30,000?"
    buttons = [{
        'url': url_for('sherpa.county_rfp'),
        'text': 'Yes'
    }, {
        'url': url_for('sherpa.multiple_purchases'),
        'text': 'No'
    }]
    prev = {
        'url': url_for('sherpa.emergency_goods'),
        'text': "Is it an emergency purchase?"
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/county-rfp-process", methods=["GET", "POST"])
def county_rfp():
    '''
    End of the county RFP flow
    '''
    title = "Use the Allegheny County RFP process."
    prev = {
        'url': url_for('sherpa.thirty_thousand'),
        'text': "Is the items cost over $30,000?"
    }
    content = '''
        <p>
          More information about the County's RFP process is coming soon. For some example RFPs, take a look at the list of
          <a href="http://apps.county.allegheny.pa.us/BidsSearch/SpecSearch.aspx">in-use contracts.</a>
        </p>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )

@blueprint.route("/multiple-purchases", methods=["GET", "POST"])
def multiple_purchases():
    '''
    Followup for non emergency purchases less than $30000
    '''
    title = "Will there be multiple purchases of this item over time?"
    buttons = [{
        'url': url_for('sherpa.service'),
        'text': 'Yes'
    }, {
        'url': url_for('sherpa.phone_single'),
        'text': 'No'
    }]
    prev = {
        'url': url_for('sherpa.thirty_thousand'),
        'text': "Is the items cost over $30,000?"
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/phone-quote-single-use", methods=["GET", "POST"])
def phone_single():
    '''
    End of the single-use less than $30000 flow
    '''
    title = "Use the phone quote process."
    prev = {
        'url': url_for('sherpa.multiple_purchases'),
        'text': "Will there be multiple purchases of this item over time?"
    }
    content = '''
        <p>
          In order to do a phone quote, you must provide the Office of Management and
          Budget's procurement team with detailed specifications and contract information
          for at least three likely bidders
        </p>
        <p>More information on the phone quote process is coming soon.</p>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )

@blueprint.route("/is-it-a-service", methods=["GET", "POST"])
def service():
    '''
    Followup for multiple purchases
    '''
    title = "Is it a service?"
    buttons = [{
        'url': url_for('sherpa.between_10_30'),
        'text': 'Yes'
    }, {
        'url': url_for('sherpa.phone_service'),
        'text': 'No'
    }]
    prev = {
        'url': url_for('sherpa.multiple_purchases'),
        'text': "Is the items cost over $30,000?"
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/phone-quote-service", methods=["GET", "POST"])
def phone_service():
    '''
    End of the service less than $10000 flow
    '''
    title = "Use the phone quote process."
    prev = {
        'url': url_for('sherpa.service'),
        'text': "Will there be multiple purchases of this item over time?"
    }
    content = '''
        <p>
          In order to do a phone quote, you must provide the Office of Management and
          Budget's procurement team with detailed specifications and contract information
          for at least three likely bidders.
        </p>
        <p>More information on the phone quote process is coming soon.</p>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )

@blueprint.route("/between-10-and-30-thousand", methods=["GET", "POST"])
def between_10_30():
    '''
    Followup for services
    '''
    title = "Is the item between $10,000 and $30,000?"
    buttons = [{
        'url': url_for('sherpa.b_bid'),
        'text': 'Yes'
    }, {
        'url': url_for('sherpa.phone_not_b'),
        'text': 'No'
    }]
    prev = {
        'url': url_for('sherpa.service'),
        'text': "Is it a service?"
    }

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/phone-quote-not-b-bid", methods=["GET", "POST"])
def phone_not_b():
    '''
    End of the < $30000 services flow
    '''
    title = "Use the phone quote process."
    prev = {
        'url': url_for('sherpa.between_10_30'),
        'text': "Is the item between $10,000 and $30,000?"
    }
    content = '''
        <p>In order to do a phone quote, you must provide the Office
        of Management and Budget's procurement team with detailed specifications
        and contract information for at least three likely bidders</p>
        <p>More information on the phone quote process is coming soon.</p>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )

@blueprint.route("/b-bid", methods=["GET", "POST"])
def b_bid():
    '''
    End of the $30000+ services flow
    '''
    title = "Use a bid inquiry (B-Bid)"
    prev = {
        'url': url_for('sherpa.between_10_30'),
        'text': "Is the item between $10,000 and $30,000?"
    }
    content = '''
        <p>More information about the B-Bid process is coming soon!</p>
    '''

    return render_template(
        "sherpa/question.html",
        title=title,
        prev=prev,
        content=content
    )
