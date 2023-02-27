from paikea.routes import (
    confirm_modem_device,
    confirm_queue,
    confirm_pairing,
    check_duplicate_route,
    check_route_for_participant,
)
import paikea.models as md


def test_no_modem(database):
    db = database
    modem_q = db.session.query(md.RockBlockModem)
    errors = confirm_modem_device(modem_q, '100', 'buoy', 'notinthere')

    exp_errors = [
        "No Source ID: 100",
    ]
    assert errors
    for err in exp_errors:
        assert err in errors


def test_bad_modem(database, create_modems):
    modems = create_modems
    db = database
    modem_q = db.session.query(md.RockBlockModem)

    bad_label = 'BadLabel'
    errors = confirm_modem_device(modem_q, '1', 'buoy', bad_label)

    assert errors

    exp_errors = [
        f'Wrong label for modem ID: 1 -> {bad_label}',
        f'Modem ID: 1 is not of type: buoy',
    ]

    for err in exp_errors:
        assert err in errors


def test_no_queue(database):
    db = database
    queue_q = db.session.query(md.SQS_Endpoint)
    errors = confirm_queue(queue_q, '100', 'sqs', 'whatever')

    assert errors

    exp_errors = [
        "No Queue ID: 100",
    ]

    for err in exp_errors:
        assert err in errors


def test_bad_queue(database, create_queues):
    queues = create_queues
    db = database

    queue_q = db.session.query(md.SQS_Endpoint)

    bad_label = 'notinthere'
    errors = confirm_queue(queue_q, '1', 'sqs', bad_label)

    assert errors

    exp_errors = [
        f"Wrong label for Queue ID: 1 -> {bad_label}",
    ]

    for err in exp_errors:
        assert err in errors


def test_good_modem(database, create_modems):
    modems = create_modems
    db = database

    modems[0].device_type = 'buoy'
    m_label = modems[0].serial

    db.session.add(modems[0])
    db.session.commit()
    modems_q = db.session.query(md.RockBlockModem)

    errors = confirm_modem_device(modems_q, '1', 'buoy', m_label)
    assert len(errors) == 0


def test_good_queue(database, create_queues):
    queues = create_queues
    db = database

    q_label = queues[0].queue_name
    queues_q = db.session.query(md.SQS_Endpoint)

    errors = confirm_queue(queues_q, '1', 'sqs', q_label)

    assert len(errors) == 0


def test_bad_pairings():
    cases = [
        (('buoy', 'pk001', 'buoy'), ["Buoy cannot target another buoy", ]),
        (('buoy', 'command', 'handset'), ['Buoy message type must be pk001', ]),
        (('handset', 'pk001', 'handset'), ['Handset cannot target another handset']),
        (('handset', 'pk001', 'buoy'), ['Handset cannot send pk001 to buoy']),
     ]

    for case in cases:
        errors = confirm_pairing(*case[0])
        assert errors

        for err in case[1]:
            assert err in errors


def test_good_pairings():
    cases = [
        ('buoy', 'pk001', 'sqs'),
        ('buoy', 'pk001', 'handset'),
        ('handset', 'pk001', 'sqs'),
        ('handset', 'command', 'buoy'),
        ('handset', 'command', 'sqs'),
    ]

    for case in cases:
        assert len(confirm_pairing(*case)) == 0


def test_duplicate_route(database, create_routes):
    routes = create_routes
    db = database
    route_q = db.session.query(md.EndpointRoute)

    r1 = routes[0]
    errors = check_duplicate_route(
        route_q,
        r1.source_device_type,
        r1.source_device,
        r1.msg_type,
        r1.endpoint_type,
        r1.endpoint_id)

    assert errors

    exp_errors = [
        f"Duplicate routes found: {r1.id}",
    ]

    for err in exp_errors:
        assert err in errors

def test_route_participant(database, create_routes):
    routes = create_routes
    db = database
    route_q = db.session.query(md.EndpointRoute)

    r1 = routes[0]

    check = check_route_for_participant(route_q,
                                r1.source_device_type,
                                r1.source_device, )
    assert check
    assert f"Routes contain item: 1, 2, 3" in check

    check = check_route_for_participant(route_q,
                                        r1.endpoint_type,
                                        r1.endpoint_id)

    assert check
    assert f"Routes contain item: 1, 3" in check

    check = check_route_for_participant(route_q,
                                        'sqs',
                                        9999)
    assert not check
