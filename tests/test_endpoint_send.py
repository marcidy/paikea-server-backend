import os
import binascii
import pytest
from unittest.mock import (
    patch,
    MagicMock
)
import paikea.models as md


@patch('paikea.models.boto3')
@patch('paikea.models.requests')
def test_SQS_send(requests, boto3, flask_app):
    ep_url = 'https://notarealtarget.url/PAIKEA_MO'
    ep = md.SQS_Endpoint(queue_name='test', url=ep_url)
    queue = MagicMock()
    queue.url = ep_url

    queues = MagicMock()
    queues.all.return_value = [queue]

    sqs_resource = MagicMock()
    sqs_resource.queues = queues

    class Resource:
        def __call__(self, x):
            if x == 'sqs':
                return sqs_resource
    _resource = Resource()
    boto3.resource = _resource

    q = ep.get_queue()
    assert q.url == ep_url

    ep.send("hi there")
    assert q.send_message.called
    assert q.send_message.called_with(MessageBody="hi there")


@patch('paikea.models.requests')
def test_rockblock_endpoint(requests, create_endpoints):
    db = create_endpoints
    msg = "This is a story all about how my life got flipped" \
        ", turned upside-down"
    enc_msg = binascii.hexlify(msg.encode('ascii')).decode('ascii')
    user = "RB_USER"
    pwrd = "RB_PASS"
    os.environ['ROCKBLOCK_USER'] = user
    os.environ['ROCKBLOCK_PASS'] = pwrd

    rb = db.session.query(md.RockBlockModem).all()[1]
    rb.send(enc_msg)
    assert requests.post.called
    url, params = requests.post.call_args[0]
    assert params['imei'] == rb.imei
    assert params['data'] == enc_msg
    assert params['username'] == user
    assert params['password'] == pwrd
    del os.environ['ROCKBLOCK_USER']
    del os.environ['ROCKBLOCK_PASS']


def test_rockblock_endpoint_no_creds(create_endpoints):
    db = create_endpoints
    msg = "This is a story all about how my life got flipped" \
        ", turned upside-down"
    # enc_msg = binascii.hexlify(msg.encode('ascii')).decode('ascii')

    rb = db.session.query(md.RockBlockModem).all()[1]
    with pytest.raises(ValueError):
        rb.send(msg)


@patch('paikea.models.requests')
def test_rockblock_endpoint_failed(requests, create_endpoints):
    db = create_endpoints
    requests.post.side_effect = ValueError("On No!!")
    rb = db.session.query(md.RockBlockModem).all()[0]
    with pytest.raises(ValueError):
        rb.send("whatever")


@patch('paikea.models.requests')
def test_rockstar_endpoint_failed(requests, create_endpoints):
    db = create_endpoints
    requests.post.side_effect = ValueError("On No!!")
    rb = db.session.query(md.RockStar).all()[0]
    with pytest.raises(ValueError):
        rb.send("whatever")


@patch('paikea.models.requests')
def test_rockstar_send(requests, create_endpoints):
    db = create_endpoints
    msg = "This is a story all about how my life got flipped" \
        ", turned upside-down"
    user = "RC_USER"
    pwrd = "RC_PASS"
    os.environ['ROCKCORE_USER'] = user
    os.environ['ROCKCORE_PASS'] = pwrd

    rs = db.session.query(md.RockStar).all()[0]
    rs.send(msg)

    assert requests.post.called
    args, kwargs = requests.post.call_args
    assert args[0] == 'https://core.rock7.com/API2/SendMessage/' + rs.serial
    params = kwargs['params']
    assert params['message'] == msg
    assert params['username'] == user
    assert params['password'] == pwrd
    del os.environ['ROCKCORE_USER']
    del os.environ['ROCKCORE_PASS']
