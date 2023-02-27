import os
from unittest.mock import patch
import paikea.models as md
import paikea.tasks as tasks
from message_fixtures import (
    single_test_rock_block_message,
    pk001,
    pk004,
    random_location,
)


def test_ep_route_create(database):
    db = database
    ep1 = md.EndpointRoute(source_device_type="rockblock",
                           source_device=1,
                           msg_type="pk001",
                           endpoint_type="sqs",
                           endpoint_id=1)
    db.session.add(ep1)
    db.session.commit()

    epr = db.session.query(md.EndpointRoute).all()
    assert len(epr) == 1


def test_eprouter_populate(create_endpoints):
    db = create_endpoints
    epr = db.session.query(md.EndpointRoute).all()
    assert len(epr) == 4


def test_eprouter_get_endpoint(create_endpoints):
    db = create_endpoints

    eprs = db.session.query(md.EndpointRoute).all()

    for epr in eprs:
        ep = epr.get_endpoint()
        assert ep
        assert ep.id == epr.endpoint_id


@patch('paikea.models.boto3')
@patch('paikea.models.requests')
def test_send_endpoints(requests, boto3, with_messages):
    os.environ['ROCKBLOCK_USER'] = 'fakeuser'
    os.environ['ROCKBLOCK_PASS'] = 'rakepass'
    os.environ['ROCKCORE_USER'] = 'fakeuser'
    os.environ['ROCKCORE_PASS'] = 'rakepass'

    db = with_messages
    msgs = db.session.query(md.RockBlockMessage).all()
    msg_ids = [msg.id for msg in msgs]

    modems = db.session.query(md.RockBlockModem).all()
    for modem in modems:
        modem.device_type = 'buoy'
        modem.device_id = 1
        db.session.add(modem)

    db.session.commit()

    for msg_id in msg_ids:
        tasks.on_new_rbm(msg_id)
        tasks.create_message(msg_id)

    eps = db.session.query(md.EndpointRoute).all()

    tasks.send_to_endpoints(1, 'buoy', 1, 'pk001')

    errs = db.session.query(md.MessageParsingError).all()
    assert not errs
