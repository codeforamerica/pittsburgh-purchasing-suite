# -*- coding: utf-8 -*-
from flask_assets import Bundle, Environment

less = Bundle(
    'less/main.less',
    filters='less',
    output='public/css/common.css',
    depends=('less/*.less', 'less/**/*.less')
)

wexplorer_less = Bundle(
    'less/wexplorer_main.less',
    filters='less',
    output='public/css/wexplorer.css',
    depends=('less/*.less', 'less/**/*.less')
)

css = Bundle(
    'libs/bootstrap/dist/css/bootstrap.css',
    'css/style.css',
    filters='cssmin',
    output='public/css/common.css'
)

js = Bundle(
    'libs/jQuery/dist/jquery.js',
    'libs/bootstrap/dist/js/bootstrap.js',
    'js/plugins.js',
    filters='jsmin',
    output='public/js/common.js'
)

assets = Environment()

assets.register('js_all', js)
assets.register('css_all', less)
assets.register('wexplorer_less', wexplorer_less)
