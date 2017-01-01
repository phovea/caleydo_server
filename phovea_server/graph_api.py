###############################################################################
# Caleydo - Visualization for Molecular Biology - http://caleydo.org
# Copyright (c) The Caleydo Team. All rights reserved.
# Licensed under the new BSD license, available at http://caleydo.org/license
###############################################################################

from .dataset_api_util import dataset_getter
from .swagger import to_json

def format_json(dataset, range, args):
  d = dataset.asjson(range)
  if bool(args.get('f_pretty_print', False)):
    return jsonify(d, indent=' ')
  return jsonify(d)


def resolve_formatter(type, format):
  from .plugin import list as list_plugins
  for p in list_plugins(type + '-formatter'):
    if p.format == format:
      return p.load()
  formats = ','.join(p.format for p in list_plugins(type + '-formatter'))
  ns.abort(400, 'unknown format "{0}" possible formats are: {1}'.format(format, formats))


def _list_items(dataset_getter, name, datasetid):
  d = dataset_getter(datasetid, 'graph')
  if ns.request.method == 'GET':
    r = asrange(ns.request.args.get('range', None))
    return jsonify([n.asjson() for n in getattr(d, name + 's')(r[0] if r is not None else None)])

  if ns.request.method == 'DELETE':
    if d.clear():
      return to_json(d.to_description(), indent=1)
    ns.abort(400)

  # post
  n = _to_desc()
  if getattr(d, 'add_' + name)(n):
    return jsonify(d.to_description(), indent=1)
  # invalid upload
  ns.abort(400)


def _handle_item(dataset_getter, name, datasetid, itemid):
  d = dataset_getter(datasetid, 'graph')
  if ns.request.method == 'GET':
    n = getattr(d, 'get_' + name)(itemid)
    return jsonify(n.asjson())

  if ns.request.method == 'DELETE':
    if getattr(d, 'remove_' + name)(itemid):
      return jsonify(d.to_description(), indent=1)
    ns.abort(400)

  # put
  n = _to_desc()
  n['id'] = itemid
  if getattr(d, 'update_' + name)(n):
    return jsonify(d.to_description(), indent=1)
  # invalid upload
  ns.abort(400)


def _list_type(dataset_getter, name='node'):
  from functools import partial
  return partial(_list_items, dataset_getter, name), partial(_handle_item, dataset_getter, name)


def get_graph(datasetid):
  d = dataset_getter(datasetid, 'graph')
  return d.to_description()


def get_graph_data(datasetid, range, pretty_print):
  d = dataset_getter(datasetid, 'graph')
  if pretty_print:
    to_json(d.to_description(), indent=' ')
  return to_json(d.to_description())

  list_nodes, handle_node = _list_type(dataset_getter, 'node')
  app.add_url_rule('/graph/<datasetid>/node', 'list_nodes', list_nodes, methods=['GET', 'POST', 'DELETE'])
  app.add_url_rule('/graph/<datasetid>/node/<int:itemid>', 'handle_node', handle_node, methods=['GET', 'PUT', 'DELETE'])

  list_edges, handle_edge = _list_type(dataset_getter, 'edge')
  app.add_url_rule('/graph/<datasetid>/edge', 'list_edges', list_edges, methods=['GET', 'POST', 'DELETE'])
  app.add_url_rule('/graph/<datasetid>/edge/<int:itemid>', 'handle_edge', handle_edge, methods=['GET', 'PUT', 'DELETE'])

  # websocket = ws.Socket(app)
  # @websocket.route('/ws')
  # def graph_ws(socket):
  #  ws.websocket_loop(socket, dict(get_graph=(payload, s)))
