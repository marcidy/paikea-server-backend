"""
Helper functions for route validation
"""
from sqlalchemy import (
    or_,
    and_,
)
from sqlalchemy.orm import exc
from paikea.extensions import db
from paikea import models as md


def check_route(data):
    src_dev_type = data['source']['type']
    src_dev_id = data['source']['id']
    src_dev_label = data['source']['label']
    src_msg_type = data['source']['msg']
    tgt_type = data['target']['type']
    tgt_id = data['target']['id']
    tgt_label = data['target']['label']

    modems_q = db.session.query(md.RockBlockModem)
    buoys_q = db.session.query(md.Buoy)
    handsets_q = db.session.query(md.Handset)
    routes_q = db.session.query(md.EndpointRoute)
    queues_q = db.session.query(md.SQS_Endpoint)

    errors = []

    if src_dev_type in ['handset', 'buoy']:
        errors.extend(
            confirm_modem_device(modems_q, src_dev_id, src_dev_type, src_dev_label))

    if tgt_type in ['handset', 'buoy']:
        errors.extend(
            confirm_modem_device(modems_q, tgt_id, tgt_type, tgt_label))

    if tgt_type == 'sqs':
        errors.extend(
            confirm_queue(queues_q, tgt_id, tgt_type, tgt_label))

    # confirm source allowed to match with target
    errors.extend(confirm_pairing(src_dev_type, src_msg_type, tgt_type))

    errors.extend(
        check_duplicate_route(routes_q,
                              src_dev_type,
                              src_dev_id,
                              src_msg_type,
                              tgt_type,
                              tgt_id))

    return errors


def confirm_modem_device(modems_q, dev_id, dev_type, dev_label):
    errors = []
    dev = None

    try:
        dev = modems_q.filter_by(id=dev_id).one()

    except exc.NoResultFound:
        errors.append(f"No Source ID: {dev_id}")

    except exc.MultipleResultsFound:
        errors.append(f"Multiple Modems for ID: {dev_id}")

    if not dev:
        return errors

    if dev_label != dev.serial:
        errors.append(f"Wrong label for modem ID: {dev_id} -> {dev_label}")

    if dev_type != dev.device_type:
        errors.append(f"Modem ID: {dev_id} is not of type: {dev_type}")

    return errors


def confirm_queue(queues_q, queue_id, queue_type, queue_label):
    errors = []
    queue = None

    try:
        queue = queues_q.filter_by(id=queue_id).one()

    except exc.NoResultFound:
        errors.append(f"No Queue ID: {queue_id}")

    except exc.MultipleResultsFound:
        errors.append(f"Multiple Queues for ID: {queue_id}")

    if not queue:
        return errors

    if queue_label != queue.queue_name:
        errors.append(f"Wrong label for Queue ID: {queue_id} -> {queue_label}")

    return errors


def confirm_pairing(src_dev_type, msg_type, tgt_dev_type):

    errors = []

    if src_dev_type == 'buoy':
        if tgt_dev_type == 'buoy':
            errors.append('Buoy cannot target another buoy')

        if msg_type != 'pk001':
            errors.append('Buoy message type must be pk001')

    if src_dev_type == 'handset':
        if tgt_dev_type == 'handset':
            errors.append('Handset cannot target another handset')

        if tgt_dev_type == 'buoy':
            if msg_type != 'command':
                errors.append(f'Handset cannot send {msg_type} to buoy')

    return errors


def check_duplicate_route(route_q, src_dev_type, src_dev_id, src_msg_type, tgt_dev_type, tgt_dev_id):
    ''' Check if a posisble new route already exists and avoid duplicates
    '''
    errors = []
    routes = route_q.filter_by(source_device_type=src_dev_type,
                               source_device=src_dev_id,
                               msg_type=src_msg_type,
                               endpoint_type=tgt_dev_type,
                               endpoint_id=tgt_dev_id).all()
    if len(routes) > 0:
        ids = ", ".join([f"{r.id}" for r in routes])
        errors.append(f"Duplicate routes found: {ids}")

    return errors


def check_route_for_participant(route_q, p_type, p_id):
    ''' When modifying the system links, they should not exist in a route.
    The route should be removed first
    '''
    routes = route_q.filter(
        or_(
            and_(
                md.EndpointRoute.source_device_type == p_type,
                md.EndpointRoute.source_device == p_id),
            and_(
                md.EndpointRoute.endpoint_type == p_type,
                md.EndpointRoute.endpoint_id == p_id)
        )).all()

    if routes:
        rids = ", ".join(f"{r.id}" for r in routes)
        return [f"Routes contain item: {rids}"]
    else:
        return []
