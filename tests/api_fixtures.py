import pytest
import paikea.models as md


@pytest.fixture(scope='function')
def create_modems(database):
    """new doc string"""
    db = database

    for x in range(10):
        db.session.add(
            md.RockBlockModem(
                imei=f"12345678{x:02}",
                modem_type="ROCKBLOCK",
                serial=f"123{x:02}"))

    db.session.commit()
    return db.session.query(md.RockBlockModem).all()


@pytest.fixture(scope='function')
def create_queues(database):
    db = database

    db.session.add(
        md.SQS_Endpoint(queue_name="queue1",
                        url="http://notareal.url/target")
    )
    db.session.add(
        md.SQS_Endpoint(queue_name="queue2",
                        url="https://thisisnotreal.tld:9001/blah")
    )
    db.session.commit()

    return db.session.query(md.SQS_Endpoint).all()


@pytest.fixture(scope='function')
def create_routes(database, create_modems, create_queues):
    db = database
    modems = create_modems
    queues = create_queues

    modems[0].device_type = 'buoy'
    modems[1].device_type = 'buoy'
    modems[2].device_type = 'handset'
    modems[3].device_type = 'hnadset'
    db.session.add(modems[0])
    db.session.add(modems[1])
    db.session.add(modems[2])
    db.session.add(modems[3])
    db.session.commit()

    modems = db.session.query(md.RockBlockModem).all()

    routes = [
        md.EndpointRoute(
            source_device_type='buoy',
            source_device=modems[0].id,
            msg_type='pk001',
            endpoint_type='handset',
            endpoint_id=modems[2].id,
            enabled=True),
        md.EndpointRoute(
            source_device_type='buoy',
            source_device=modems[0].id,
            msg_type='pk001',
            endpoint_type='sqs',
            endpoint_id=queues[0].id,
            enabled=True),
        md.EndpointRoute(
            source_device_type='handset',
            source_device=modems[2].id,
            msg_type='command',
            endpoint_type='buoy',
            endpoint_id=modems[0].id,
            enabled=True),
    ]

    for r in routes:
        db.session.add(r)

    db.session.commit()
    return db.session.query(md.EndpointRoute).all()
