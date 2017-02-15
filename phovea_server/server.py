###############################################################################
# Caleydo - Visualization for Molecular Biology - http://caleydo.org
# Copyright (c) The Caleydo Team. All rights reserved.
# Licensed under the new BSD license, available at http://caleydo.org/license
###############################################################################
from __future__ import absolute_import
import gevent.monkey
import logging.config

gevent.monkey.patch_all()  # ensure the standard libraries are patched


# set configured registry
def _get_config():
  from . import config
  return config.view('phovea_server')


# append the plugin directories as primary lookup path
cc = _get_config()
# configure logging
logging.config.dictConfig(cc.logging)
_log = logging.getLogger(__name__)


def _add_no_cache_header(response):
  """
  disable caching on the response
  :param response:
  :return:
  """
  #  response.headers['Last-Modified'] = datetime.now()
  response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
  response.headers['Pragma'] = 'no-cache'
  response.headers['Expires'] = '-1'
  return response


def _to_stack_trace():
  import traceback
  return traceback.format_exc()


def _exception_handler(error):
  return 'Internal Server Error\n' + _to_stack_trace(), 500


def _init_app(app, is_default_app=False):
  """
  initializes an application by setting common properties and options
  :param app:
  :param is_default_app:
  :return:
  """
  from . import security

  if hasattr(app, 'debug'):
    app.debug = cc.debug
  if cc.nocache and hasattr(app, 'after_request'):
    app.after_request(_add_no_cache_header)
  if cc.error_stack_trace and hasattr(app, 'register_error_handler'):
    app.register_error_handler(500, _exception_handler)

  if cc.secret_key:
    app.config['SECRET_KEY'] = cc.secret_key

  if cc.max_file_size:
    app.config['MAX_CONTENT_LENGTH'] = cc.max_file_size

  security.init_app(app)
  if is_default_app:
    security.add_login_routes(app)


# helper to plugin in function scope
def _loader(p):
  _log.info('add application: ' + p.id + ' at namespace: ' + p.namespace)

  def load_app():
    app = p.load().factory()
    _init_app(app)
    return app

  return load_app, True


def _swagger_loader(p):
  _log.info('add swagger application: ' + p.id + ' at namespace: ' + p.namespace)

  def load_app():
    import connexion
    _log.info(p.plugin.folder)
    app = connexion.App(p.name, specification_dir=p.plugin.base_dir)
    app.add_api(p.swaggerFile, base_path=p.namespace)
    flask_app = app.app
    _init_app(flask_app)
    return flask_app

  return load_app, False


def create_application():
  from . import dispatcher
  from . import mainapp
  from .plugin import list as list_plugins
  from werkzeug.contrib.fixers import ProxyFix

  # create a path dispatcher
  default_app = mainapp.default_app()
  _init_app(default_app, True)
  applications = {p.namespace: _loader(p) for p in list_plugins('namespace')}
  swagger = {p.namespace: _swagger_loader(p) for p in list_plugins('swagger')}
  applications.update(swagger)

  # create a dispatcher for all the applications
  application = dispatcher.PathDispatcher(default_app, applications)
  return ProxyFix(application)


def create(parser):
  parser.add_argument('--port', '-p', type=int, default=cc.getint('port'),
                      help='server port')
  parser.add_argument('--address', '-a', default=cc.get('address'),
                      help='server address')

  def _launcher(args):
    from geventwebsocket.handler import WebSocketHandler
    from gevent.pywsgi import WSGIServer
    application = create_application()
    http_server = WSGIServer((args.address, args.port), application, handler_class=WebSocketHandler)

    return http_server.serve_forever

  return _launcher
