#!/usr/bin/env python

import os
import sys
import paikea.models as md
from paikea.extensions import db


if os.environ.get("FLASK_APP") != 'autoapp':
    print("Set AUTOAPP envvar")
    sys.exit(1)


sqs_endpoints = [
    (
        "Paikea Testing",
        'https://us-east-2.queue.amazonaws.com/400013730524/test_paikea_mo'
    ),
    (
        "TNC Paikea MO",
        'https://us-east-2.queue.amazonaws.com/400013730524/PAIKEA_MO'
    ),
]


routing_table = [
    ['buoy', '13760', 'pk001', 'sqs', 'Paikea Testing'],
    ['buoy', '13760', 'pk001', 'sqs', 'TNC Paikea MO'],
    ['buoy', '13760', 'pk001', 'handset', '17458'],
    ['buoy', '202841', 'pk001', 'sqs', 'TNC Paikea MO'],
    ['buoy', '202841', 'pk001', 'handset', '17458'],
    ['handset', '17458', 'command', 'buoy', '202841'],
]


adapters = {
    'buoy': {
        'table': md.RockBlockModem,
        'lookup': 'serial',
    },
    'handset': {
        'table': md.RockBlockModem,
        'lookup': 'serial',
    },
    'sqs': {
        'table': md.SQS_Endpoint,
        'lookup': 'queue_name',
    },
    'rockstar': {
        'table': md.RockStar,
        'lookup': 'serial',
    },
}


def adapt_route(route):
    src_model = adapters[route[0]]['table']
    src_filter = {adapters[route[0]]['lookup']: route[1]}
    try:
        src = db.session.query(src_model).filter_by(**src_filter).one()
    except Exception as e:
        print(f"Source not found: {src_filter}")
        raise e

    ep_model = adapters[route[3]]['table']
    ep_filter = {adapters[route[3]]['lookup']: route[4]}
    try:
        ep = db.session.query(ep_model).filter_by(**ep_filter).one()
    except Exception as e:
        print(f"Endpoint not found: {ep_filter}")
        raise e

    return {'source_device': src.id,
            'source_device_type': route[0],
            'msg_type': route[2],
            'endpoint_id': ep.id,
            'endpoint_type': route[3]}


def build_table():
    for route in routing_table:
        route_data = adapt_route(route)
        try:
            db.session.query(md.EndpointRoute).filter_by(**route_data).one()
            print(f"Found route: {route}")
        except Exception:
            print(f"Adding route: {route}")
            epr = md.EndpointRoute(**route_data)
            db.session.add(epr)
            db.session.commit()


def read_table():
    table = db.session.query(md.EndpointRoute).all()
    for rt in table:
        ep = rt.get_endpoint()
        ep_field = getattr(ep, adapters[rt.endpoint_type]['lookup'])
        src = rt.get_source()
        src_field = getattr(src, adapters[rt.source_device_type]['lookup'])
        line = f"{rt.source_device_type} {src_field} {rt.msg_type} -> {rt.endpoint_type} {ep_field}"
        print(line)


def prune_table():
    to_prune = []
    table = db.session.query(md.EndpointRoute).all()

    for rt in table:
        ep = rt.get_endpoint()
        ep_field = getattr(ep, adapters[rt.endpoint_type]['lookup'])
        src = rt.get_source()
        src_field = getattr(src, adapters[rt.source_device_type]['lookup'])
        entry = [rt.source_device_type,
                 src_field,
                 rt.msg_type,
                 rt.endpoint_type,
                 ep_field]
        if entry not in routing_table:
            print("{} not found, needs pruning".format(rt.id))
            to_prune.append(rt)

    while to_prune:
        rt = to_prune.pop()
        print(f"Pruning {rt}")
        db.session.delete(rt)

    try:
        db.session.commit()
    except Exception as e:
        print("Committing failed")
        db.session.rollback()
        raise e


def add_endpoints():
    for ep in sqs_endpoints:
        q = db.session.query(
            md.SQS_Endpoint
        ).filter_by(
            queue_name=ep[0], url=ep[1]
        ).all()

        if len(q) == 0:
            print("Adding SQS queue {} {}".format(ep[0], ep[1]))
            db.session.add(md.SQS_Endpoint(queue_name=ep[0], url=ep[1]))
        elif len(q) == 1:
            print("Found SQS queue {} {}".format(ep[0], ep[1]))
        elif len(q) > 1:
            print("Error, multiple SQS found for {} {}".format(ep[0], ep[1]))

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        print("Error committing SQS enpoints")
