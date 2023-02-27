from utils import ROCKBLOCK_INCOMING
from core_push_api_data import (gps_msg, ird_msg, ack_msg)
from paikea.extensions import db
import paikea.models as md


def test_rockblock_incoming(client):
    msg_data = ROCKBLOCK_INCOMING[0]
    result = client.post('/rockblock/incoming', data=msg_data)
    assert result.data == b'OK'
    msg = db.session.query(md.RockBlockMessage).one()
    assert msg
    assert msg.status
    assert msg.status.status == 'new'


def test_rockstar_incoming(client):
    result = client.post('/rockstar/incoming', json=ird_msg)
    assert result.data == b'OK'
    msg = db.session.query(md.RockCorePushAPI).all()
    assert msg
