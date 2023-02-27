import os
import binascii
import requests
import sqlite3
import paikea.models as md
from paikea.extensions import db


def parse_req(raw_data):
    data = raw_data.decode('ascii').split("&")
    ret = {}
    for item in data:
        k, v = item.split("=")
        ret[k] = v

    return ret


def test_payload(payload):
    data = {
        'imei': '300434063836590',
        'device_type': 'ROCKBLOCKTEST',
        'serial': '123456',
        'momsn': '441',
        'transmit_time': '20-03-15 22:12:51',
        'iridium_latitude': '37.7740',
        'iridium_longitude': '-122.4050',
        'iridium_cep': '2.0',
        'iridium_session_status': '0',
        'data': payload,
    }

    requests.post("http://localhost:8888/rockblock/incoming", data=data)


def make_test_req():
    data = {
        'imei': '300434063836590',
        'device_type': 'ROCKBLOCKTEST',
        'serial': '123456',
        'momsn': '441',
        'transmit_time': '20-03-15 22:12:51',
        'iridium_latitude': '37.7740',
        'iridium_longitude': '-122.4050',
        'iridium_cep': '2.0',
        'iridium_session_status': '0',
        'data': '504b3030313b6c61743a333737362e343339352c4e533a4e2c6c6f6e3a31323233352e35363233342c45573a572c7574633a3137343534342e36393333',  # NOQA
    }

    requests.post("http://127.0.0.1:8888/rockblock/incoming", data=data)


def get_rb_credentials():
    user = os.environ.get("ROCKBLOCK_USER")
    pword = os.environ.get("ROCKBLOCK_PASS")
    if user is not None and pword is not None:
        return user, pword
    else:
        raise ValueError("RB USER/PASS environ not set!")


def send_rbm(imei, msg):
    url = "https://core.rock7.com/rockblock/MT"
    foo, bar = get_rb_credentials()
    data = binascii.hexlify(msg.encode('ascii')).decode('ascii')
    data = {'imei': imei,
            'data': data,
            'username': foo,
            'password': bar}
    resp = None
    try:
        resp = requests.post(url, data)
    except Exception:
        print("RockBlock request failed!")
    if not resp:
        print("RockBlock resp is None but didn't fail!")
    else:
        print("Resp: {}".format(resp))
        return resp


def make_request_from_dict(data_dict):
    keys = ['imei', 'device_type', 'serial', 'momsn',
            'transmit_time', 'iridium_latitude', 'iridium_longitude',
            'iridium_cep', 'iridium_session_status', 'data']
    missing_keys = []
    extra_keys = []
    for key in keys:
        if key not in data_dict:
            missing_keys.append(key)

    for key in data_dict:
        if key not in keys:
            extra_keys.append(key)

    if len(missing_keys) != 0:
        msg = "Missing keys: {}".format(missing_keys)
        raise ValueError(msg)

    if len(extra_keys) != 0:
        msg = "Extra keys: {}".format(extra_keys)
        raise ValueError(msg)

    # r = request.post("http://localhost:8888/raw", data=values)


def get_msgs_from_sqlite(sqlite_file):
    keys = ['imei', 'device_type', 'serial', 'momsn',
            'transmit_time', 'iridium_latitude', 'iridium_longitude',
            'iridium_cep', 'iridium_session_status', 'data']

    conn = sqlite3.connect(sqlite_file)
    conn.row_factory = sqlite3.Row

    q_str = 'select {} from rock_block_message'.format(", ".join(keys))
    q = conn.execute(q_str)
    for row in q.fetchall():
        print(dict(row))
        requests.post("http://localhost:8888/raw", data=dict(row))


def drop_message_data():
    for model in (md.MessageParsingError,
                  md.PK001,
                  md.PK004,
                  md.RBMessageStatus,
                  md.RockBlockMessage):

        for msg in db.session.query(model):
            db.session.delete(msg)
    db.session.commit()
