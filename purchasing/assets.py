# -*- coding: utf-8 -*-
import os
from flask_assets import Bundle, Environment

less = Bundle(
    'less/main.less',
    filters='less',
    output='public/css/common.css',
    depends=('less/*.less', 'less/**/*.less', 'less/**/**/*.less')
)

wexplorer_less = Bundle(
    'less/wexplorer_main.less',
    filters='less',
    output='public/css/wexplorer.css',
    depends=('less/*.less', 'less/**/*.less', 'less/**/**/*.less')
)

sherpa_less = Bundle(
    'less/sherpa_main.less',
    filters='less',
    output='public/css/sherpa.css',
    depends=('less/*.less', 'less/**/*.less', 'less/**/**/*.less')
)

opportunities_less = Bundle(
    'less/opportunities_main.less',
    filters='less',
    output='public/css/opportunities.css',
    depends=('less/*.less', 'less/**/*.less')
)

conductor_less = Bundle(
    'less/conductor_main.less',
    filters='less',
    output='public/css/conductor.css',
    depends=('less/*.less', 'less/**/*.less')
)

ie8 = Bundle(
    'libs/html5shiv/dist/html5shiv.js',
    'libs/html5shiv/dist/html5shiv-printshiv.js',
    'libs/respond/dest/respond.min.js',
    filters='uglifyjs',
    output='public/js/html5shiv.js'
)

vendorjs = Bundle(
    'libs/jquery/dist/jquery.js',
    'libs/bootstrap/dist/js/bootstrap.js',
    'libs/bootstrap-datepicker/js/bootstrap-datepicker.js',
    filters='uglifyjs',
    output='public/js/common.js'
)

opportunitiesjs = Bundle(
    'js/shared/categories.js',
    'js/opportunities/*.js',
    filters='uglifyjs',
    output='public/js/beacon.js'
)

wexplorerjs = Bundle(
    'js/wexplorer/*.js',
    filters='uglifyjs',
    output='public/js/wexplorer.js'
)

conductorjs = Bundle(
    'js/shared/categories.js',
    'js/conductor/*.js',
    'libs/datatables/media/js/jquery.dataTables.js',
    'libs/select2/dist/js/select2.full.js',
    filters='uglifyjs',
    output='public/js/conductor.js'
)

assets = Environment()
test_assets = Environment()

# register our javascript bundles
assets.register('ie8', ie8)
assets.register('vendorjs', vendorjs)
assets.register('opportunitiesjs', opportunitiesjs)
assets.register('wexplorerjs', wexplorerjs)
assets.register('conductorjs', conductorjs)

# register our css bundles
assets.register('css_all', less)
assets.register('wexplorer_less', wexplorer_less)
assets.register('sherpa_less', sherpa_less)
assets.register('opportunities_less', opportunities_less)
assets.register('conductor_less', conductor_less)
