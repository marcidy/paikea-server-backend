import pytest
import paikea.formatters as formats
import paikea.tasks as tasks
import paikea.models as md


def test_no_msg(with_messages):
    with pytest.raises(Exception):
        formats.get_msg(md.RockBlockMessage, 100)


def test_incorrect_formatter(with_messages):
    db = with_messages

    assert formats.formatter_router('notreal', 'againnotreal') is None
    assert formats.formatter_router('pk001', 'notreal') is None


def test_formatters():
    assert formats.formatter_router('pk001', 'sqs') == formats.PK001_to_SQS
    assert formats.formatter_router('pk001', 'handset') == formats.PK001_to_Handset
    assert formats.formatter_router('pk001', 'rockstar') == formats.PK001_to_Rockstar
    assert formats.formatter_router('pk004', 'handset') == formats.PK004_to_Handset


def test_msg_formatting(with_messages):
    db = with_messages
    msg_ids = [msg.id for msg in db.session.query(md.RockBlockMessage).all()]

    for msg_id in msg_ids:
        tasks.on_new_rbm(msg_id)
        tasks.create_message(msg_id)

    pk001_id = db.session.query(md.PK001).one().id
    pk004_id = db.session.query(md.PK004).one().id

    assert formats.formatter_router('pk001', 'sqs')(pk001_id)
    assert formats.formatter_router('pk001', 'handset')(pk001_id)
    assert formats.formatter_router('pk001', 'rockstar')(pk001_id)
    assert formats.formatter_router('pk004', 'handset')(pk004_id)
