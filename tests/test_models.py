import binascii
from paikea import models
from datetime import datetime
from core_push_api_data import (
    gps_msg,
    ird_msg,
    ack_msg,
)


def test_RockBlockMessage():
    payload = binascii.hexlify("This is a test.".encode('ascii'))

    model_data = {
        'imei': 'ABCDEFGHI1234567890111234',
        'device_type': 'ROCKBLOCKTEST',
        'serial': "17645",
        'momsn': '44',
        'transmit_time': '20-03-15 22:12:51',
        'iridium_latitude': '37.7740',
        'iridium_longitude': "-122.4050",
        'iridium_cep': '2.5',
        'iridium_session_status': '0',
        'data': payload}

    rbm = models.RockBlockMessage(**model_data)

    assert rbm
    for k, v in model_data.items():
        assert getattr(rbm, k) == model_data[k]

    assert rbm.created_at is None
    assert rbm.logical_del is None

    rbm_dict = rbm.to_dict()
    for k, v in rbm_dict.items():
        assert model_data[k] == v


def test_RBMessageStatus():
    rbstatus = models.RBMessageStatus(rbm_id=1, status="new")
    assert rbstatus.rbm_id == 1
    assert rbstatus.status == "new"


def test_RockBlockModem():
    test_data = {
        'imei': "ABDEFGHI1234567891011234",
        'device_type': "ROCKBLOCKTEST",
        'serial': "17394",
        'momsn': "1000",
        'status': "Live",
    }

    rbm = models.RockBlockModem(**test_data)
    assert rbm
    for k, v in test_data.items():
        assert getattr(rbm, k) == test_data[k]

    del rbm
    test_data['device_id'] = 100
    test_data['device_type'] = 'handset'
    rbm = models.RockBlockModem(**test_data)

    assert rbm.device_id == 100
    assert rbm.device_type == 'handset'
    for k, v in test_data.items():
        assert getattr(rbm, k) == v


def test_Buoy():
    test_data = {
        'id': 10,
        'firmware_version': 'v0.1.2-b3',
    }
    buoy = models.Buoy(**test_data)

    assert buoy
    assert buoy.id == 10
    assert buoy.firmware_version == 'v0.1.2-b3'


def test_PK001():
    test_data = {
        'id': 100,
        'rbm_id': 1202,
        'ird_transmit_time': datetime(2020, 4, 3, 12, 34, 22),
        'ird_latitude': 37.1234,
        'ird_longitude': -122.24354,
        'ird_cep': 5.3,
        'device_transmit_time': datetime(2020, 4, 3, 12, 30, 57),
        'device_latitude': 37.4235,
        'device_longitude': -122.94739,
        'device_NS': "N",
        'device_EW': "W",
        'device_batt': 3.5,
    }

    msg = models.PK001(**test_data)
    assert msg

    for k, v in test_data.items():
        assert getattr(msg, k) == v


def test_MessageParsingError():

    test_data = {
        'id': 10938,
        'msg_source': "RockBlock",
        'msg_id': "asd;lkf38u4jaklsf",
        'error': "cant parse!",
        'error_status': "new",
    }

    mpe = models.MessageParsingError(**test_data)
    assert mpe

    for k, v in test_data.items():
        assert getattr(mpe, k) == v


def test_RockCorePushAPI_gps():
    msg = gps_msg.copy()
    msg.pop('JWT')
    rcp_msg = models.RockCorePushAPI(**msg)
    assert rcp_msg
    for k, v in msg.items():
        assert getattr(rcp_msg, k) == v


def test_RockCorePushAPI_ird():
    msg = ird_msg.copy()
    msg.pop('JWT')
    rcp_msg = models.RockCorePushAPI(**msg)
    assert rcp_msg
    for k, v in msg.items():
        assert getattr(rcp_msg, k) == v


def test_RockCorePushAPI_ack():
    msg = ack_msg.copy()
    msg.pop('JWT')
    rcp_msg = models.RockCorePushAPI(**msg)
    assert rcp_msg
    for k, v in msg.items():
        assert getattr(rcp_msg, k) == v


def test_rockstar():
    test_data = {'imei': "011232312341234",
                 'serial': "23456",
                 'device_type': "ROCKSTAR", }
    rockstar = models.RockStar(**test_data)
    assert rockstar
    for k, v in test_data.items():
        assert getattr(rockstar, k) == v


def test_sqs_endpoint():
    test_data = {
        'queue_name': 'Paikea_MO',
        'url': 'https://us-east-2.queue.amazonaws.com/400013730524/PAIKEA_MO',
    }
    sqs = models.SQS_Endpoint(**test_data)
    assert sqs
    for k, v in test_data.items():
        assert getattr(sqs, k) == v
