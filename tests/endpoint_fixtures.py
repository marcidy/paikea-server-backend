import binascii
import pytest
from message_fixtures import pk001, pk004
import paikea.models as md


@pytest.fixture(scope='function')
def create_endpoints(database):
    db = database
    ep1 = md.SQS_Endpoint(queue_name='PAIKEA_MO',
                          url='https://notarealendpoint.zzz/target')
    ep2 = md.SQS_Endpoint(queue_name='OTHER',
                          url='https://againnotarealendpoint.zzz/blah')
    rockstar = md.RockStar(imei="Thisisanid",
                           device_type="ROCKSTAR",
                           serial="12345")
    rockblock1 = md.RockBlockModem(imei="1234567890",
                                   device_type="ROCKBLOCK",
                                   serial="98765",
                                   status="Live")
    rockblock2 = md.RockBlockModem(imei="112233445566",
                                   device_type="ROCKBLOCK",
                                   serial="44444",
                                   status="Live")
    db.session.add(ep1)
    db.session.add(ep2)
    db.session.add(rockstar)
    db.session.add(rockblock1)
    db.session.add(rockblock2)
    db.session.commit()

    er1 = md.EndpointRoute(source_device_type='buoy',
                           source_device=rockblock1.id,
                           msg_type='pk001',
                           endpoint_type='sqs',
                           endpoint_id=ep1.id)
    db.session.add(er1)

    er2 = md.EndpointRoute(source_device_type='buoy',
                           source_device=rockblock1.id,
                           msg_type='pk001',
                           endpoint_type='handset',
                           endpoint_id=rockblock2.id)
    db.session.add(er2)
    er3 = md.EndpointRoute(source_device_type='buoy',
                           source_device=rockblock1.id,
                           msg_type='pk001',
                           endpoint_type='rockstar',
                           endpoint_id=rockstar.id)
    db.session.add(er3)

    er4 = md.EndpointRoute(source_device_type='buoy',
                           source_device=rockblock1.id,
                           msg_type='pk004',
                           endpoint_type='handset',
                           endpoint_id=rockblock2.id)
    db.session.add(er4)
    return db


@pytest.fixture(scope='function')
def with_messages(database, create_endpoints):
    # test creating pk001 and pk004 messages and routing them to endpoints
    db = create_endpoints
    rb1 = db.session.query(md.RockBlockModem).filter_by(imei='1234567890').one()

    loc_data = {
        'lat': 3745.6588,
        'lon': -12243.8766,
        'ns': "N",
        'ew': "W",
        'utc': 220000.000,
        'sog': 3.4,
        'cog': 33.4,
        'sta': '4',
    }
    pkt_1 = binascii.hexlify(pk001(loc_data).encode('ascii')).decode('ascii')
    rbm_1 = md.RockBlockMessage(
        imei=rb1.imei,
        device_type="ROCKBLOCKTEST",
        serial=rb1.serial,
        momsn=rb1.momsn,
        transmit_time="20-03-15 22:12:51",
        iridium_latitude='37.7740',
        iridium_longitude='-122.4050',
        iridium_cep='2.0',
        iridium_session_status='0',
        data=pkt_1
    )
    pkt_2 = binascii.hexlify(pk004(loc_data).encode('ascii')).decode('ascii')
    rbm_2 = md.RockBlockMessage(
        imei=rb1.imei,
        device_type="ROCKBLOCKTEST",
        serial=rb1.serial,
        momsn=rb1.momsn,
        transmit_time="20-03-15 22:12:51",
        iridium_latitude='37.7740',
        iridium_longitude='-122.4050',
        iridium_cep='2.0',
        iridium_session_status='0',
        data=pkt_2
    )
    rbm_1.status = md.RBMessageStatus(status='new')
    rbm_2.status = md.RBMessageStatus(status='new')

    db.session.add(rbm_1)
    db.session.add(rbm_2)
    db.session.commit()
    return db
