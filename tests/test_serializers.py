from paikea import serializers
from paikea import models
from paikea.extensions import db
from core_push_api_data import (
    gps_msg,
    ird_msg,
    ack_msg
)


def test_StatusSchema():
    schema = serializers.StatusSchema()
    assert schema

    status = models.RBMessageStatus(rbm_id=1, status="new")
    out = schema.dumps(status)
    assert out is not None
    assert 'status' in out
    assert out == '{"status": "new"}'


def test_RBModemSchema():
    schema = serializers.RBModemSchema()
    assert schema

    test_data = {
        'imei': "ABCDEF12345678909",
        'modem_type': "ROCKBLOCKTEST",
        'serial': "169443",
        'momsn': 999,
        'status': "live",
        'device_id': 42,
        'device_type': 'buoy',
    }

    rbm = models.RockBlockModem(**test_data)
    out = schema.dump(rbm)
    for k, v in test_data.items():
        assert k in out
        assert out[k] == v


def test_BuoySchema():
    schema = serializers.BuoySchema()
    assert schema

    test_data = {
        'id': 22,
        'firmware_version': 'v0.2.1-b3',
    }
    buoy = models.Buoy(**test_data)
    out = schema.dump(buoy)
    for k, v in test_data.items():
        assert out[k] == v


def test_RockCorePushAPI():
    rcp = serializers.RockCorePushAPI()
    assert rcp

    msg = gps_msg.copy()
    msg.pop("JWT")
    msg_instance = rcp.load(msg, transient=True)
    for k, v in msg.items():
        assert getattr(msg_instance, k) == v
