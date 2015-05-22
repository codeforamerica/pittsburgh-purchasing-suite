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

js = Bundle(
    'libs/jQuery/dist/jquery.js',
    'libs/bootstrap/dist/js/bootstrap.js',
    filters='uglifyjs',
    output='public/js/common.js'
)

assets = Environment()
test_assets = Environment()

assets.register('js_all', js)
assets.register('css_all', less)
assets.register('wexplorer_less', wexplorer_less)
assets.register('sherpa_less', sherpa_less)
