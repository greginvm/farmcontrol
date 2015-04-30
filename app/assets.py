from os import path

from flask.ext.assets import Bundle, Environment


moment_js = Bundle(
    'moment/moment.js',
    'moment/locale/sl.js',
    filters='rjsmin'
)

base_js = Bundle(
    'jquery/dist/jquery.js',
    'underscore/underscore.js',
    'bootstrap/dist/js/bootstrap.js',
    'bootstrap-toggle/js/bootstrap-toggle.js',
    moment_js,
    filters='rjsmin',
    output='base_all.js'
)

base_css = Bundle(
    'bootswatch-dist/css/bootstrap.css',
    'bootstrap-toggle/css/bootstrap-toggle.css',
    filters='cssmin',
    output='base_all.css'
)

highcharts_js = Bundle(
    'highstock-release/highstock.js',
    'highstock-release/highcharts-more.js',
    'custom/highstock/dark-no-unica.js',
    filters='rjsmin',
    output='highcharts_all.js'
)

dashboard_js = Bundle(
    'espresso.js/espresso.min.js',
    'custom/util.js',
    'custom/dashboard_charts.js',
    'custom/dashboard.js',
    filters='rjsmin',
    output='dashboard_all.js'
)

datgui_js = Bundle(
    'dat.gui/dat.gui.js',
    filters='rjsmin',
    output='datgui_all.js'
)

fontawesome = Bundle('font-awesome/css/font-awesome.css',
                     output='fonts/font-awesome.css')

fonts = (('font-awesome/fonts/', 'FontAwesome.otf'),
         ('font-awesome/fonts/', 'fontawesome-webfont.eot'),
         ('font-awesome/fonts/', 'fontawesome-webfont.svg'),
         ('font-awesome/fonts/', 'fontawesome-webfont.ttf'),
         ('font-awesome/fonts/', 'fontawesome-webfont.woff'))

charts_js = Bundle(
    'custom/util.js',
    'custom/charts.js',
    filters='rjsmin',
    output='charts_all.js'
)

assets_env = Environment()


def init_app(app):
    assets_env.init_app(app)
    assets_env.app = app
    assets_env.register('base_css', base_css)
    assets_env.register('base_js', base_js)
    assets_env.register('highcharts_js', highcharts_js)
    assets_env.register('dashboard_js', dashboard_js)
    assets_env.register('charts_js', charts_js)
    assets_env.register('fontawesome_css', fontawesome)
    assets_env.register('datgui_js', datgui_js)

    assets_env.load_path = [
        path.join(path.dirname(__file__), 'bower_components'),
        path.join(path.dirname(__file__), 'static')
    ]
