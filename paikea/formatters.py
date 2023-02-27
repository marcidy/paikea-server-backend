"""
When messages are being sent from the server, they must be formatted for the
specific endpoint.  The functions of this module look up messages by ID from
the database and format the messages for each enpoint.

The FORMATTER_TABLE contains the actual mapping for the functions as a nested
dict of [<message type>][<destination>] = formatter
"""
import binascii
import simplejson as json
import paikea.models as md
from paikea.extensions import db
from paikea.paikea_protocol import convert_nmea


def get_msg(model, m_id):
    ''' Helper function to retrieve a record from the table linked to model
    by m_id'''
    try:
        return db.session.query(model).filter_by(id=m_id).one()
    except Exception as e:
        print(f"Cannot retrieve single source message {model}: {m_id}")
        raise e


def PK001_to_SQS(pd_id):
    """ Formats a PK001 message for an SQS destination"""
    msg = get_msg(md.PK001, pd_id)

    if msg:
        rbm = get_msg(md.RockBlockMessage, msg.rbm_id)
        return json.dumps(rbm.to_dict())


def PK001_to_Rockstar(pd_id):
    """ Formats a PK001 message for a RockStar destination """
    msg = get_msg(md.PK001, pd_id)
    out = f"{msg.device_transmit_time}:  {msg.device_latitude} {msg.device_NS},"\
        f" {msg.device_longitude} {msg.device_EW}"
    return out


def PK001_to_Handset(pd_id):
    """ Formats a PK001 message for a handset destination via Iridium
    RockBlock API"""
    msg = get_msg(md.PK001, pd_id)
    if msg:
        lat = convert_nmea(float(msg.device_latitude))   # convert to DDMM.mmmm
        lon = convert_nmea(abs(float(msg.device_longitude)))  # convert to DDDMM.mmmm
        ns = msg.device_NS
        ew = msg.device_EW
        cog = msg.device_cog
        sog = msg.device_sog
        sta = msg.device_status
        ts = msg.device_transmit_time  # convert to HHMMSS.000
        utc = f"{ts.hour:02}{ts.minute:02}{ts.second:02}.0000"
        pkt = f"PK004,{lat},{ns},{lon},{ew},{sog},{cog},{utc},{sta}"
        out = "+DATA:" + pkt
        out = out.replace(";", ",", 1)  # reformat packet for iridium receiver
        out = binascii.hexlify(out.encode('ascii')).decode('ascii')
        return out


def PK004_to_Handset(pd_id):
    """ Formats a PK004 message for a handset destination via Iridium RockBlock
    API"""
    msg = get_msg(md.PK004, pd_id)
    if msg:
        rbm = get_msg(md.RockBlockMessage, msg.rbm_id)
        out = "+DATA:" + binascii.unhexlify(rbm.data).decode('ascii')
        out = out.replace(";", ",", 1)  # reformat packet for iridium receiver
        return out.encode('ascii')


def Command_to_Buoy(cmd_id):
    """ Formats a DeviceCommand message for a Buoy destination via Iridium
    RockBlock API"""
    msg = get_msg(md.DeviceCommandMessage, cmd_id)
    cmd = None
    if msg:
        if msg.command == "beacon" or msg.command == "PK005":
            if msg.value == "ON" or msg.value == "1":
                cmd = "+DATA:PK005,1;"
            elif msg.value == "OFF" or msg.value == "0":
                cmd = "+DATA:PK005,0;"
        if msg.command == "update" or msg.command == "PK006":
            cmd = "+DATA:PK006,{};".format(int(msg.value))

        cmd = binascii.hexlify(cmd.encode('ascii')).decode('ascii')
        return cmd


FORMATTER_TABLE = {
    'pk001': {
        'sqs': PK001_to_SQS,
        'handset': PK001_to_Handset,
        'rockstar': PK001_to_Rockstar, },
    'pk004': {
         'handset': PK004_to_Handset, },
    'command': {
        'buoy': Command_to_Buoy, }
}


def formatter_router(msg_type, end_point_type):
    """ Retrieves proper formatter based on message type and endpoint type.

    :param msg_type: Type of message as a string based on first keys in FROMATTER_TABLE
    :param end_point_type: Type of endpoint as second key in FORMATTER_TABLE
    """
    if msg_type not in FORMATTER_TABLE:
        print(f"No serializer not found for msg_type {msg_type}")
        return

    if end_point_type not in FORMATTER_TABLE[msg_type]:
        print(f"No endpoint found for msg_type {msg_type}, {end_point_type}")
        return

    return FORMATTER_TABLE[msg_type][end_point_type]
