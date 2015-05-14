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
    pre_button_content = [{'title':'What are you doing?', 'content':'Need to start a contract or wondering which process you should use to buy something? Get started by selecting an option below!'}]
    buttons = [{'url':url_for('sherpa.index'),'text':'Start a contract!'},{'url':url_for('sherpa.buy_something'),'text':'Buy something!'}]

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
    buttons = [{'url':url_for('sherpa.index'),'text':'Yes'},{'url':url_for('sherpa.sourcing'),'text':'No'},{'url':'../wexplorer','text':"I don't know"}]
    prev = {'url':url_for('sherpa.index'),'text':'Getting started'}

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/what-are-you-sourcing", methods=["GET", "POST"])
def sourcing():
    '''
    Second question for the buy something flow
    '''
    title = "What are you sourcing?"
    buttons = [{'url':url_for('sherpa.prof_services'),'text':'Professional Services'},{'url':url_for('sherpa.goods_services'),'text':'Goods/Services'},{'url':'../wexplorer','text':"Construction"}]
    prev = {'url':url_for('sherpa.buy_something'),'text':'Is it on contract?'}
    content = ""

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev,
        content=content
    )

@blueprint.route("/professional-services", methods=["GET", "POST"])
def prof_services():
    '''
    First question for professional services sub-flow
    '''
    title = "Is it an emergency?"
    buttons = [{'url':url_for('sherpa.wallace'),'text':'Yes'},{'url':url_for('sherpa.sole_source'),'text':'No'}]
    prev = {'url':url_for('sherpa.sourcing'),'text':'What are you sourcing?'}

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )

@blueprint.route("/wallace-act", methods=["GET", "POST"])
def wallace():
    '''
    End of professional services flow if an emergency
    '''
    title = "Use the Wallace Act Process"
    prev = {'url':url_for('sherpa.prof_services'),'text':'Is it an emergency?'}
    content = "The Wallace Act covers the emergency purchase of goods and services not on a contract whose costs exceed $2,000. These purchases will require City Council approval after the fact.<p>More information about the Wallace Act is coming soon.</p>"

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
    buttons = [{'url':url_for('sherpa.sole_rfp'),'text':'Yes'},{'url':url_for('sherpa.dept_rfp'),'text':'No'}]
    prev = {'url':url_for('sherpa.prof_services'),'text':'Is it an emergency?'}

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
    prev = {'url':url_for('sherpa.sole_source'),'text':'Is there only one supplier?'}
    content = "<p>Sole source agreements are unique professional service agreements which may include subscriptions, sometimes include maintenance/warranty work on equipment.</p><p>According to a 2009 City of Pittsburgh policy document,</p><blockquote><p>a <strong>Sole Source Professional Services contract</strong> is a contract involving unique professional services that are documented to be available from one source only. An example could be art restoration by a particular artist on his or her own work. The term may also include specialized training or maintenance services on verified sole-source purchases.</p></blockquote><p>More information about sole source contracts is coming soon.</p>"

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
    prev = {'url':url_for('sherpa.sole_source'),'text':'Is there only one supplier?'}
    content = '<p>More information about RFPs and the RFP writing process is coming soon. For some reference materials, take a look at the list of currently open contract bids in the following places:</p><ul><li><a href="http://pittsburghpa.gov/omb/contract-bids">Office of Management and Budget</a></li><li><a href="http://pittsburghpa.gov/dcp/rfp-rfq">Department of City Planning</a></li><li><a href="http://www.pgh2o.com/doing-business">Pittsburgh Water and Sewer Authority</a></li><li><a href="http://www.ura.org/working_with_us/proposals.php">Urban Redevelopment Authority of Pittsburgh</a></li></ul>'

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
    buttons = [{'url':url_for('sherpa.explanatory'),'text':'Yes'},{'url':url_for('sherpa.emergency_goods'),'text':'No'}]
    prev = {'url':url_for('sherpa.sourcing'),'text':'What are you sourcing?'}

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
    prev = {'url':url_for('sherpa.goods_services'),'text':"Is the item's cost under $2000?"}
    content = '<p>The Explanatory Process allows you to purchase an item whose total cost is $2,000 or less without a contract. However, this purchase must receive <em>pre-approval</em> from both the Director of your department and the Director of the Office of Management and Budget, and final approval from City Council.</p>'

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
    buttons = [{'url':url_for('sherpa.wallace'),'text':'Yes'},{'url':url_for('sherpa.emergency_goods'),'text':'No'}]
    prev = {'url':url_for('sherpa.goods_services'),'text':"Is the item's cost under $2,000?"}

    return render_template(
        "sherpa/question.html",
        title=title,
        buttons=buttons,
        prev=prev
    )