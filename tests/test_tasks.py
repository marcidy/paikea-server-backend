import time
import pytest
from message_fixtures import (
    single_test_rock_block_message,
    pk001,
    pk004,
    pk005,
    pk006
)
import paikea.tasks as tasks
import paikea.models as md
import paikea.paikea_protocol as protocol


def count_mpes(db):
    return len(db.session.query(md.MessageParsingError).all())


def test_on_new_rbm_task(database, flask_app, celery_worker):
    db = database
    msg = single_test_rock_block_message("nothing particular")
    msg.status = md.RBMessageStatus(status='new')
    db.session.add(msg)
    db.session.commit()
    msg_id = msg.id

    tasks.on_new_rbm(msg.id)
    new_rbm = db.session.query(md.RockBlockMessage)\
        .filter_by(id=msg_id).one()

    assert new_rbm
    assert new_rbm.status.status == 'processing'

    modem = db.session.query(md.RockBlockModem)\
        .filter_by(serial=new_rbm.serial).one()
    assert modem
    modem.device_type = 'buoy'
    modem.device_id = 1
    db.session.add(modem)
    db.session.commit()


@pytest.mark.celery
def test_pk001_msg_task(database, flask_celery_app,
                        celery_session_worker, celery_app):
    db = database
    with flask_celery_app.app_context():
        loc_data = {
            'lat': 3779.1234,
            'lon': 12256.64322,
            'utc': 104355.9374,
            'ns': 'N',
            'ew': 'W',
            'cog': '167.3',
            'sog': '2.5',
            'batt': '3.2',
        }
        msg = single_test_rock_block_message(pk001(loc_data))
        msg.status = md.RBMessageStatus(status='new')
        db.session.add(msg)
        db.session.commit()
        msg_id = msg.id

        result = tasks.on_new_rbm.delay(msg_id)
        while not result.ready():
            time.sleep(.1)
        # tasks.create_message(msg.id)
        pk001_msg = db.session.query(md.PK001).filter_by(rbm_id=msg_id).one()
        assert pk001_msg
        assert pk001_msg.device_NS == "N"
        assert pk001_msg.device_EW == "W"
        assert float(pk001_msg.device_latitude) == \
            pytest.approx(protocol.convert_degdm(str(loc_data['lat'])))
        assert -float(pk001_msg.device_longitude) == \
            pytest.approx(protocol.convert_degdm(str(loc_data['lon'])))


@pytest.mark.celery
def test_pk004_msg_task(database, flask_celery_app,
                        celery_session_worker, celery_app):
    db = database
    with flask_celery_app.app_context():
        loc_data = {
            'lat': 3779.1234,
            'lon': 12256.64322,
            'utc': 104355.9374,
            'ns': 'N',
            'ew': 'W',
            'sog': '3.4',
            'cog': '23.5'
        }
        msg = single_test_rock_block_message(pk004(loc_data))
        msg.status = md.RBMessageStatus(status='new')
        db.session.add(msg)
        db.session.commit()
        msg_id = msg.id

        result = tasks.on_new_rbm.delay(msg_id)
        while not result.ready():
            time.sleep(.1)

        pk004_msg = db.session.query(md.PK004).filter_by(rbm_id=msg_id).one()
        assert pk004_msg
        assert pk004_msg.ns == "N"
        assert pk004_msg.ew == "W"
        assert float(pk004_msg.lat) == \
            pytest.approx(protocol.convert_degdm(str(loc_data['lat'])))
        assert float(pk004_msg.lon) == \
            pytest.approx(protocol.convert_degdm(str(loc_data['lon'])))
        assert pk004_msg.cog == float(loc_data['cog'])
        assert pk004_msg.sog == float(loc_data['sog'])


@pytest.mark.celery
def test_pk005_msg_task(database, flask_celery_app,
                        celery_session_worker, celery_app):
    db = database
    with flask_celery_app.app_context():
        payload = pk005(True)
        assert payload == "PK005;1"
        msg = single_test_rock_block_message(payload)
        msg.status = md.RBMessageStatus(status='new')
        db.session.add(msg)
        db.session.commit()
        msg_id = msg.id
        result = tasks.on_new_rbm.delay(msg_id)

        while not result.ready():
            time.sleep(.1)

        cmd = db.session.query(md.DeviceCommandMessage).filter_by(source_msg_id=msg_id).one()
        assert cmd
        assert cmd.command == "PK005"
        assert cmd.value == "1"


def test_on_parsing_error(database, flask_celery_app,
                          celery_session_worker, celery_app):
    db = database
    with flask_celery_app.app_context():
        tasks.on_parsing_error(src="rockblock",
                               mid="45",
                               error="This is an error all about how")

        # need to fix this once i fix the addition of modems with device_type
        mpe = db.session.query(md.MessageParsingError).all()[-1]
        assert mpe.msg_source == 'rockblock'
        assert mpe.msg_id == "45"
        assert mpe.error == "This is an error all about how"
        assert mpe.error_status == "new"
