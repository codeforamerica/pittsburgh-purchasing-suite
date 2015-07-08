# -*- coding: utf-8 -*-

from purchasing.sherpa.viewblocks import QuestionNode, TerminationNode

class Index(QuestionNode):
    title = 'Explore the Pittsburgh Procurement Process!'
    pre_button_content = [{
        'title': 'What are you doing?',
        'content': '''
            Need to start a contract or wondering which process you should use to buy
            something? Get started by selecting an option below!
        '''
    }]
    buttons = [{
        'url': 'StartPSA',
        'text': 'Start a contract!'
    }, {
        'url': 'BuySomething',
        'text': 'Buy something!'
    }]

class StartPSA(TerminationNode):
    '''
    Termination node for starting a new professional
    services agreement
    '''
    title = 'Start a Professional Services Agreement'
    left_content_description = "The professional services agreement is the last step in the RFP process. It is drafted by the legal department based on the information and documents provided throughout that process provided by the RFP committee's point person."
    steps = [
        {
            'title': "You'll need to know",
            'format': 'list',
            'todos': [
                "Name of point person for RFP", "List of other departments participating in RFP",
                "1-2 Sentence Description of Professional Services to be rendered",
                "Proposed start date for Agreement",
            ]
        }, {
            'title': 'Gather required documents',
            'format': 'infoboxes',
            'todos': [
                "Scope of work section from RFP", "Project budget",
                "Awarded vendor's proposal in response to RFP",
                "Awarded vendor's current insurance certificate",
            ]
        }, {
            'title': 'Complete Request Form',
            'format': 'extlink',
            'external': True,
            'extlink_description': "Once you're ready, fill in the form and upload required documents at the link below",
            'url': 'https://cfa.typeform.com/to/gLWMLC',
            'button_text': 'Start PSA Request Form'
        }
    ]
    timeline = [
        {'body': "Prepare documents and information"},
        {'body': "Complete and submit request form"},
        {'body': "Your request is submitted to a solicitor"},
        {'body': "Solicitor approves request and asks you to make changes"},
        {'body': "You send approved professional services agreement to awarded vendor for approval"},
        {'body': "Vendor's legal department and City Solicitor agree on a final Professional Services Agreement. Vendor signs four hard copies and sends them to you"},
        {'body': "You gather signatures from your Department Director, the Director of Finance, the Director of OMB, and your solicitor before you submit the agreement to the Controller's Office"},
        {'body': "Once the City Controller approves, your PSA is finalized, and you can begin to work with your awarded vendor"}
    ]

    prev = {
        'url': 'Index',
        'text': 'Getting Started'
    }

class BuySomething(QuestionNode):
    '''First question for the buy something flow
    '''
    title = 'Is it on contract?'
    buttons = [{
        'url': 'UseIt',
        'text': 'Yes'
    }, {
        'url': 'Sourcing',
        'text': 'No'
    }, {
        'url': '../scout',
        'external': True,
        'text': "I don't know",
        'new_tab': True
    }]
    prev = {
        'url': 'Index',
        'text': 'Getting started'
    }

class UseIt(QuestionNode):
    '''For those who don't really need to use this app
    '''
    title = "Buy or use it!"
    prev = {
        'url': 'Index',
        'text': 'Getting started'
    }

class Sourcing(QuestionNode):
    '''Second question for the buy something flow
    '''
    title = 'What are you sourcing?'
    buttons = [{
        'url': 'EmergencyProfessionalServices',
        'text': 'Professional Services'
    }, {
        'url': 'GoodsServices',
        'text': 'Goods/Services'
    }, {
        'url': 'Construction',
        'text': "Construction"
    }]
    prev = {
        'url': 'BuySomething',
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

class Construction(QuestionNode):
    '''End of the construction flow
    '''
    title = "Use the construction process."
    prev = {
        'url': 'Sourcing',
        'text': "What are you sourcing?"
    }
    content = '<p>More information about the construction process coming soon!</p>'

class EmergencyProfessionalServices(QuestionNode):
    '''First question for professional services sub-flow
    '''
    title = 'Is it an emergency?'
    buttons = [{
        'url': 'WallaceActProfessionalServices',
        'text': 'Yes'
    }, {
        'url': 'SoleSource',
        'text': 'No'
    }]
    prev = {
        'url': 'Sourcing',
        'text': 'What are you sourcing?'
    }

class WallaceActProfessionalServices(QuestionNode):
    '''End of emergency professional services flow
    '''
    title = 'Use the Wallace Act Process'
    prev = {
        'url': 'EmergencyProfessionalServices',
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

class SoleSource(QuestionNode):
    '''First question for professional services sub-flow
    '''
    title = 'Is there only one supplier (sole sourced)?'
    buttons = [{
        'url': 'SoleSourceRFP',
        'text': 'Yes'
    }, {
        'url': 'DepartmentSoleSourceRFP',
        'text': 'No'
    }]
    prev = {
        'url': 'EmergencyProfessionalServices',
        'text': 'Is it an emergency?'
    }

class SoleSourceRFP(QuestionNode):
    '''End of sole source professional services flow
    '''
    title = 'Write a sole source RFP'
    prev = {
        'url': 'SoleSource',
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

class DepartmentSoleSourceRFP(QuestionNode):
    '''End of competitive bid professional services flow
    '''
    title = 'Write and issue a department RFP'
    prev = {
        'url': 'SoleSource',
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

class GoodsServices(QuestionNode):
    '''First question for goods/services flow
    '''
    title = "Is the item's cost under $2,000?"
    buttons = [{
        'url': 'Explanatory',
        'text': 'Yes'
    }, {
        'url': 'EmergencyGoods',
        'text': 'No'
    }]
    prev = {
        'url': 'Sourcing',
        'text': 'What are you sourcing?'
    }

class Explanatory(QuestionNode):
    '''End of the explanatory process flow
    '''
    title = 'Use the Explanatory Process'
    prev = {
        'url': 'GoodsServices',
        'text': "Is the item's cost under $2000?"
    }
    content = '''
        <p>The Explanatory Process allows you to purchase an item whose total cost is
        $2,000 or less without a contract. However, this purchase must receive
        <em>pre-approval</em> from both the Director of your department and the Director
        of the Office of Management and Budget, and final approval from City Council.</p>
    '''

class EmergencyGoods(QuestionNode):
    '''Followup for goods/services flow
    '''
    title = 'Is it an emergency purchase?'
    buttons = [{
        'url': 'WallaceGoods',
        'text': 'Yes'
    }, {
        'url': 'OverThirtyThousand',
        'text': 'No'
    }]
    prev = {
        'url': 'GoodsServices',
        'text': "Is the item's cost under $2,000?"
    }

class WallaceGoods(QuestionNode):
    '''End of emergency goods flow
    '''
    title = "Use the Wallace Act Process"
    prev = {
        'url': 'EmergencyGoods',
        'text': 'Is it an emergency?'
    }
    content = '''
        <p>The Wallace Act covers the emergency purchase of goods and services not on a contract
        whose costs exceed $2,000. These purchases will require City Council approval after
        the fact.</p>
        <p>More information about the Wallace Act is coming soon.</p>
    '''

class OverThirtyThousand(QuestionNode):
    '''Followup for non emergency purchases more than $2000
    '''
    title = "Is the items cost over $30,000?"
    buttons = [{
        'url': 'CountyRFPProcess',
        'text': 'Yes'
    }, {
        'url': 'MultiplePurchases',
        'text': 'No'
    }]
    prev = {
        'url': 'EmergencyGoods',
        'text': "Is it an emergency purchase?"
    }

class CountyRFPProcess(QuestionNode):
    '''
    End of the county RFP flow
    '''
    title = "Use the Allegheny County RFP process."
    prev = {
        'url': 'OverThirtyThousand',
        'text': "Is the items cost over $30,000?"
    }
    content = '''
        <p>
          More information about the County's RFP process is coming soon. For some example RFPs, take a look at the list of
          <a href="http://apps.county.allegheny.pa.us/BidsSearch/SpecSearch.aspx">in-use contracts.</a>
        </p>
    '''

class MultiplePurchases(QuestionNode):
    '''Followup for non emergency purchases less than $30000
    '''
    title = "Will there be multiple purchases of this item over time?"
    buttons = [{
        'url': 'IsItAService',
        'text': 'Yes'
    }, {
        'url': 'PhoneQuoteSingleUse',
        'text': 'No'
    }]
    prev = {
        'url': 'OverThirtyThousand',
        'text': "Is the items cost over $30,000?"
    }

class PhoneQuoteSingleUse(QuestionNode):
    '''End of the single-use less than $30000 flow
    '''
    title = "Use the phone quote process."
    prev = {
        'url': 'MultiplePurchases',
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

class IsItAService(QuestionNode):
    '''Followup for multiple purchases
    '''
    title = "Is it a service?"
    buttons = [{
        'url': 'Between10And30',
        'text': 'Yes'
    }, {
        'url': 'PhoneQuoteService',
        'text': 'No'
    }]
    prev = {
        'url': 'MultiplePurchases',
        'text': "Is the items cost over $30,000?"
    }

class PhoneQuoteService(QuestionNode):
    '''End of the service less than $10000 flow
    '''
    title = "Use the phone quote process."
    prev = {
        'url': 'IsItAService',
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

class Between10And30(QuestionNode):
    '''Followup for services
    '''
    title = "Is the item between $10,000 and $30,000?"
    buttons = [{
        'url': 'BBid',
        'text': 'Yes'
    }, {
        'url': 'PhoneQuoteNotBBid',
        'text': 'No'
    }]
    prev = {
        'url': 'IsItAService',
        'text': "Is it a service?"
    }

class PhoneQuoteNotBBid(QuestionNode):
    '''End of the < $30000 services flow
    '''
    title = "Use the phone quote process."
    prev = {
        'url': 'Between10And30',
        'text': "Is the item between $10,000 and $30,000?"
    }
    content = '''
        <p>In order to do a phone quote, you must provide the Office
        of Management and Budget's procurement team with detailed specifications
        and contract information for at least three likely bidders</p>
        <p>More information on the phone quote process is coming soon.</p>
    '''

class BBid(QuestionNode):
    '''End of the $30000+ services flow
    '''
    title = "Use a bid inquiry (B-Bid)"
    prev = {
        'url': 'Between10And30',
        'text': "Is the item between $10,000 and $30,000?"
    }
    content = '''
        <p>More information about the B-Bid process is coming soon!</p>
    '''
