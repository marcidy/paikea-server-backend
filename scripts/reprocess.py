from paikea.extensions import db
import paikea.models as md
from paikea.tasks import send_to_endpoints


def resend(source_type, msg_type, msg, endpoint_type=None):
    rbm_id = msg.rbm_id
    rbm = db.session.query(md.RockBlockMessage).filter_by(id=rbm_id).one()
    modem_id = rbm.rb.id
    send_to_endpoints.delay(modem_id, source_type, msg.id, msg_type)
