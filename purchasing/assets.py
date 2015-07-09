# -*- coding: utf-8 -*-
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

vendorjs = Bundle(
    'libs/jQuery/dist/jquery.js',
    'libs/bootstrap/dist/js/bootstrap.js',
    'libs/bootstrap-datepicker/js/bootstrap-datepicker.js',
    filters='uglifyjs',
    output='public/js/common.js'
)

opportunitiesjs = Bundle(
    'js/opportunities/*.js',
    filters='uglifyjs',
    output='public/js/opportunities.js'
)

wexplorerjs = Bundle(
    'js/wexplorer/*.js',
    filters='uglifyjs',
    output='public/js/wexplorer.js'
)

conductorjs = Bundle(
    'js/conductor/*.js',
    filters='uglifyjs',
    output='public/js/conductor.js'
)

assets = Environment()
test_assets = Environment()

# register our javascript bundles
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
