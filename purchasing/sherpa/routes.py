# -*- coding: utf-8 -*-

from flask import Blueprint
from purchasing.sherpa.viewblocks import register_endpoint, URL_PREFIX
from purchasing.sherpa.views import (
    Index, StartPSA, BuySomething, UseIt, Sourcing, Construction,
    EmergencyProfessionalServices, WallaceActProfessionalServices,
    SoleSource, SoleSourceRFP, DepartmentSoleSourceRFP, GoodsServices,
    Explanatory, EmergencyGoods, WallaceGoods, OverThirtyThousand,
    CountyRFPProcess, MultiplePurchases, PhoneQuoteSingleUse,
    IsItAService, PhoneQuoteService, Between10And30, PhoneQuoteNotBBid,
    BBid
)

blueprint = Blueprint(
    URL_PREFIX.lstrip('/'), __name__, url_prefix=URL_PREFIX,
    static_folder='../static', template_folder='../templates'
)

register_endpoint(blueprint, Index('/'))
register_endpoint(blueprint, StartPSA())
register_endpoint(blueprint, BuySomething())
register_endpoint(blueprint, UseIt())
register_endpoint(blueprint, Sourcing())
register_endpoint(blueprint, Construction())
register_endpoint(blueprint, EmergencyProfessionalServices())
register_endpoint(blueprint, WallaceActProfessionalServices())
register_endpoint(blueprint, SoleSource())
register_endpoint(blueprint, SoleSourceRFP())
register_endpoint(blueprint, DepartmentSoleSourceRFP())
register_endpoint(blueprint, GoodsServices())
register_endpoint(blueprint, Explanatory())
register_endpoint(blueprint, EmergencyGoods())
register_endpoint(blueprint, WallaceGoods())
register_endpoint(blueprint, OverThirtyThousand())
register_endpoint(blueprint, CountyRFPProcess())
register_endpoint(blueprint, MultiplePurchases())
register_endpoint(blueprint, PhoneQuoteSingleUse())
register_endpoint(blueprint, IsItAService())
register_endpoint(blueprint, PhoneQuoteService())
register_endpoint(blueprint, Between10And30())
register_endpoint(blueprint, PhoneQuoteNotBBid())
register_endpoint(blueprint, BBid())
