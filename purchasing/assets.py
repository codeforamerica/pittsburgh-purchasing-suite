# -*- coding: utf-8 -*-
from flask_assets import Bundle, Environment

less = Bundle(
    'less/main.less',
    filters='less',
    output='public/css/common.css',
    depends=('less/*.less', 'less/**/*.less', 'less/**/**/*.less')
)

scout_less = Bundle(
    'less/scout_main.less',
    filters='less',
    output='public/css/scout.css',
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
    'libs/moment/moment.js',
    'libs/eonasdan-bootstrap-datetimepicker/src/js/bootstrap-datetimepicker.js',
    filters='uglifyjs',
    output='public/js/common.js'
)

publicjs = Bundle(
    'js/shared/extlink.js',
    filters='uglifyjs',
    output='public/js/public.js')

opportunitiesjs = Bundle(
    'js/shared/*.js',
    'js/opportunities/*.js',
    filters='uglifyjs',
    output='public/js/opportunities.js'
)

scoutjs = Bundle(
    'js/scout/*.js',
    'js/shared/extlink.js',
    filters='uglifyjs',
    output='public/js/scout.js'
)

conductorjs = Bundle(
    'libs/datatables/media/js/jquery.dataTables.js',
    'libs/jquery.dirtyforms/jquery.dirtyforms.js',
    'libs/select2/dist/js/select2.js',
    'libs/d3/d3.js',
    'libs/c3/c3.js',
    'js/shared/*.js',
    'js/conductor/*.js',
    filters='uglifyjs',
    output='public/js/conductor.js'
)

adminjs = Bundle(
    'libs/jquery/dist/jquery.js',
    'libs/jquery-ui/ui/core.js',
    'libs/jquery-ui/ui/widget.js',
    'libs/jquery-ui/ui/mouse.js',
    'libs/jquery-ui/ui/sortable.js',
    'libs/moment/moment.js',
    'libs/bootstrap/dist/js/bootstrap.js',
    'libs/select2/dist/js/select2.full.js',
    'libs/eonasdan-bootstrap-datetimepicker/src/js/bootstrap-datetimepicker.js',
    filters='uglifyjs',
    output='public/js/admin.js'
)

admin_less = Bundle(
    'less/admin_main.less',
    filters='less',
    output='public/css/admin.css',
    depends=('less/*.less', 'less/**/*.less')
)

assets = Environment()
test_assets = Environment()

# register our javascript bundles
assets.register('ie8', ie8)
assets.register('vendorjs', vendorjs)
assets.register('publicjs', publicjs)
assets.register('adminjs', adminjs)
assets.register('opportunitiesjs', opportunitiesjs)
assets.register('scoutjs', scoutjs)
assets.register('conductorjs', conductorjs)

# register our css bundles
assets.register('css_all', less)
assets.register('admin_less', admin_less)
assets.register('scout_less', scout_less)
assets.register('opportunities_less', opportunities_less)
assets.register('conductor_less', conductor_less)
