import os
import shutil
from sqlalchemy.orm.exc import NoResultFound
from flask import current_app as app
import git
from paikea.extensions import (
    db,
    make_celery,
)
import paikea.models as md
from paikea.paikea_protocol import (
    transmit_time_to_datetime,
    buoy_time_to_datetime,
    convert_degdm,
    parse_iridium_payload,
    parse_rockcore_payload,
)
from paikea.formatters import formatter_router
from paikea.firmware_utils import UpgradeStatus


ce_app = make_celery(app)


@ce_app.task
def create_pk001(rbm_id, data):
    """ Transforms an incoming RockBlock message into a default
    location message, which is packet type PK001.  This task is
    run by the router after an incoming message message has been
    serialized to the database and routed by packet type.

    If the PK001 message is successfully created, this task triggers the
    send_to_endpoints task, which will forward the message on to any endpoint
    defined in the EndpointRoute table.

    :param int rbm_id: source RockBlockMessage id
    :param dict data: Output from parse_iridium_payload
    """
    ddata = {}
    for item in data['fields']:
        k, v = item.split(":")
        ddata[k] = v

    rbm = db.session.query(md.RockBlockMessage).filter_by(id=rbm_id).one()
    modem_id = rbm.rb.id

    ird_transmit_time = transmit_time_to_datetime(rbm.transmit_time)
    ird_lat = float(rbm.iridium_latitude)
    ird_lon = float(rbm.iridium_longitude)
    ird_cep = float(rbm.iridium_cep)

    device_time = buoy_time_to_datetime(ddata['utc'], ird_transmit_time)

    device_NS = ddata['NS']
    device_lat = convert_degdm(ddata['lat'])
    if device_NS.upper() == "S":
        device_lat = -device_lat

    device_EW = ddata['EW']
    device_lon = convert_degdm(ddata['lon'])
    if device_EW.upper() == "W":
        device_lon = -device_lon

    try:
        device_batt = float(ddata['batt'])
    except (ValueError, KeyError):
        device_batt = 0

    device_status = int(ddata.get('sta', 0))
    try:
        device_cog = float(ddata['cog'])
    except ValueError:
        device_cog = 0

    try:
        device_sog = float(ddata['sog'])
    except ValueError:
        device_sog = 0

    pm = md.PK001(
        rbm_id=rbm_id,
        ird_transmit_time=ird_transmit_time,
        ird_latitude=ird_lat,
        ird_longitude=ird_lon,
        ird_cep=ird_cep,
        device_transmit_time=device_time,
        device_latitude=device_lat,
        device_longitude=device_lon,
        device_NS=device_NS,
        device_EW=device_EW,
        device_batt=device_batt,
        device_cog=device_cog,
        device_sog=device_sog,
        device_status=device_status,
    )

    db.session.add(pm)

    try:
        db.session.commit()
    except Exception as e:
        print("comitting PikeaMessage failed!")
        db.session.rollback()
        raise e

    try:
        modem = db.session.query(md.RockBlockModem).filter_by(id=modem_id).one()
    except Exception as e:
        print("problem finding modem {}, cannot send".format(modem_id))
        print(e)

    if modem.device_type not in ['buoy', 'handset']:
        print("Ambiguous device type for modem {}: {}".format(modem.id,
                                                              modem.device_type))

    if pm.id:
        send_to_endpoints(modem_id, modem.device_type, pm.id, 'pk001')


@ce_app.task
def create_pk004(rbm_id, data):
    """ Transforms an incoming RockBlock message into a location and
    velocity message, which is packet type PK004.

    This task is run by the router after an incoming message message has been
    serialized to the database and routed by packet type.

    If the PK004 message is successfully created, this task triggers the
    send_to_endpoints task, which will forward the message on to any endpoint
    defined in the EndpointRoute table.

    :param int rbm_id: source RockBlockMessage id
    :param dict data: Output from parse_iridium_payload
    """

    # session = db.create_scoped_session()
    rbm = db.session.query(md.RockBlockMessage).filter_by(id=rbm_id).one()
    modem_id = rbm.rb.id

    ird_transmit_time = transmit_time_to_datetime(rbm.transmit_time)
    fields = data['fields']
    msg_time = None
    msg = None

    try:
        utc = fields[6]
        msg_time = buoy_time_to_datetime(fields[6], ird_transmit_time)
    except Exception:
        print(f"Error parsing PK004 time: {rbm_id} {fields}")

    try:
        lat = convert_degdm(fields[0])
        ns = fields[1]
        lon = convert_degdm(fields[2])
        ew = fields[3]
        sog = float(fields[4])
        cog = float(fields[5])
        if msg_time:
            utc = msg_time
        else:
            utc = ird_transmit_time
        msg = md.PK004(rbm_id=rbm_id, lat=lat, ns=ns,
                       lon=lon, ew=ew, sog=sog, cog=cog,
                       utc=utc)
    except Exception as e:
        print(f"Error parsing PK004 fields: {fields}")
        raise e

    if msg:
        db.session.add(msg)
        try:
            db.session.commit()
        except Exception as e:
            print(f"Committing PK004 failed: {rbm_id} {fields}")
            db.session.rollback()
            raise e

    if msg.id:
        send_to_endpoints(modem_id, 'buoy', msg.id, 'pk004')


@ce_app.task
def on_new_rbm(rbm_id):
    ''' Process a new RockBlockMessage object

    Transitions message status from 'new' to 'processing' and finds or creates
    the modem associated witih the message.  If successful, triggers the
    create_message task.


    :param int rbm_id: RockBlockMessage id
    '''
    # session = db.create_scoped_session()
    rbm = db.session.query(md.RockBlockMessage).filter_by(id=rbm_id).one()

    if rbm.status.status != 'new':
        return

    rbm.status.status = 'processing'
    db.session.add(rbm)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    modems = db.session.query(md.RockBlockModem).filter_by(imei=rbm.imei).all()

    if len(modems) == 0:
        print("No RockBlockModem imei: {} found, creating".format(rbm.imei))
        modem = md.RockBlockModem(
            imei=rbm.imei,
            modem_type=rbm.device_type,
            serial=rbm.serial)

        db.session.add(modem)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            msg = "Failed creating new RockBlockModem: {}"
            raise ValueError(msg.format(rbm.imei))

    elif len(modems) == 1:
        print("Found RockBlockModem for imei: {}".format(rbm.imei))
        modem = modems[0]

    elif len(modems) > 1:
        msg = "Multiple RockBlockModems with imei: {}"
        print(msg.format(rbm.imei))
        raise ValueError(msg.format(rbm.imei))

    if not rbm.rb:
        rbm.rb = modem
        db.session.add(rbm)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    create_message.delay(rbm_id)

# def get_mo_queue():
#     """ Finds the PAIKEA_MO SQS queue url using boto3
#     :returns str: URL of PAIKEA_MO SQS queue
#     """
#     for queue in boto3.resource('sqs').queues.all():
#         if "PAIKEA_MO" in queue.url:
#             return queue
#     raise ValueError("Boto3 cannot find PAIKEA_MO sqs queue!")
#
#
# def send_to_sqs():
#     ''' Grabs all messages in 'processing' state from the db and
#     attempts to send to SQS PAIKEA_MO queue
#     '''
#     mo_q = get_mo_queue()
#     msgs = (db.session.query(md.RockBlockMessage, md.RBMessageStatus)
#             .filter(md.RockBlockMessage.id == md.RBMessageStatus.rbm_id,
#                     md.RBMessageStatus.status == 'processing')).all()
#     for msg in msgs:
#         try:
#             mo_q.send_message(MessageBody=json.dumps(msg.to_dict()))
#             msg.status.status == 'sent'
#         except Exception:
#             print("Failed to send msg to SQS: {}".format(msg))
#
#         if msg.status.status == 'sent':
#             db.session.add(msgs)
#             try:
#                 db.session.commit()
#             except Exception:
#                 db.session.rollback()
#                 print("Error commiting messages!")
#
#
# @ce_app.task
# def send_rbm_to_sqs(rbm_id):
#     ''' Send single RockBlockMessage to AWS SQS PAIKEA_MO queue
#     :param msg RockBlockMessage: RockBlockMessage database object
#     '''
#     msg = db.session.query(md.RockBlockMessage).filter_by(id=rbm_id).one()
#     mo_q = get_mo_queue()
#     try:
#         mo_q.send_message(MessageBody=json.dumps(msg.to_dict()))
#         msg.status.status == 'sent'
#     except Exception:
#         print("Failed to send msg to SQS: {}".format(msg))
#
#     if msg.status.status == 'sent':
#         db.session.add(msg)
#         try:
#             db.session.commit()
#         except Exception:
#             db.session.rollback()
#             print("Error commiting messages!")


@ce_app.task
def send_beacon(rbm_id, data):
    """ Send a command to a buoy to toggle the beacon function.

    :param int rbm_id: id of source message triggering this command
    :param dict data: payload data indicating command value
    """
    rbm = db.session.query(md.RockBlockMessage).filter_by(id=rbm_id).one()
    modem_id = rbm.rb.id
    kwargs = {
        'command': "PK005",
        'value': data['fields'][0],  # This needs to be 1 or 0 for PK005
        'source_msg_type': "handset",
        'source_msg_id': rbm.id,
        'source_device_type': "handset",
        'source_device_id': modem_id
    }
    cmd = md.DeviceCommandMessage(**kwargs)
    db.session.add(cmd)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error("Problem committing command: {}".format(kwargs),
                         exc_info=True)
        print(e)
    if cmd.id:
        send_to_endpoints(modem_id, 'handset', cmd.id, 'command')


@ce_app.task
def update_beacon_interval(rbm_id, data):
    """ Send a command to a buoy to change the frequency of it's update period.

        :param rbm_id: id of source message triggering this command
        :param data: payload data indicating command value
    """

    rbm = db.session.query(md.RockBlockMessage).filter_by(id=rbm_id).one()
    modem_id = rbm.rb.id
    kwargs = {
        'command': 'PK006',
        'value': data['fields'][0],  # should be 0-9999 int
        'source_msg_type': 'handset',
        'source_msg_id': rbm.id,
        'source_device_type': 'handset',
        'source_device_id': modem_id
    }
    cmd = md.DeviceCommandMessage(**kwargs)
    db.session.add(cmd)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error("Problem committing command: {}".format(kwargs),
                         exc_info=True)
        print(e)

    if cmd.id:
        send_to_endpoints(modem_id, 'handset', cmd.id, 'command')


msg_router = {
    "PK001": create_pk001,
    "PK004": create_pk004,
    "PK005": send_beacon,  # Beacon toggle
    "PK006": update_beacon_interval,  # Beacon interval
}


def on_parsing_error(src, mid, error):
    """When a message produces an error during processing, create an
        error report

        :param str src: Source of the error message
        :param int mid: Message causing error
        :param str error: Error message
    """
    # session = db.create_scoped_session()
    em = md.MessageParsingError(
        msg_source=src,
        msg_id=mid,
        error=error,
        error_status="new")
    db.session.add(em)
    try:
        db.session.commit()
    except Exception:
        print(f"Well, comitting the parsing error failed.\
              src:{src}, msg_id:{mid}, prob: {error}")
        db.session.rollback()


@ce_app.task
def create_message(rbm_id):
    """ Parses iridium payload from a RockBlockMessage and processes
        the message via the router.

        :param int rbm_id: Source RockBlockMessage id
    """
    source = "Iridium"
    msg_id = str(rbm_id)
    # session = db.create_scoped_session()
    rbm = db.session.query(md.RockBlockMessage).filter_by(id=rbm_id).one()

    try:
        data = parse_iridium_payload(rbm.data)
    except Exception:
        app.logger.error("Create message failed", exc_info=True)
        on_parsing_error(source, msg_id, "Payload parsing failed")
        return

    if 'msg_type' not in data:
        on_parsing_error(source, msg_id, f'No msg_type!')

    if data['msg_type'] not in msg_router:
        on_parsing_error(source, msg_id, f'No router for {data["msg_type"]}')

    try:
        msg_router[data['msg_type']](rbm_id, data)
    except Exception as e:
        on_parsing_error(source, msg_id, f"{e}")


@ce_app.task
def send_to_endpoints(source, source_type, msg_id, message_type):
    """ Based on message source and type, routes the contents of a message to
        an endpoint based on the routed defined in the EndpointRoute table.

        This is the final step in processing incoming messages, which is to
        format the outgoing data for the destination, and call the
        destination's send method on the formatted data.

        :param int source: id of the source of the message
        :param str source_type: Device type which sent the source message
        :param int msg_id: the id of the messate in the table referred to by message_type
        :param str message_type: the type of the message
    """
    if source_type not in md.EndpointRoute.source_device_types:
        msg = f"Invalid source type: {source_type}"
        raise ValueError(msg)

    filter = {'source_device_type': source_type,
              'source_device': source,
              'msg_type': message_type,
              'enabled': True, }

    epts = db.session.query(md.EndpointRoute).filter_by(**filter).all()

    n_epts = len(epts)
    lm = f"{source_type} {source} {message_type}: {n_epts} Endpoints"
    app.logger.warning(lm)

    for ept in epts:
        f_msg = formatter_router(message_type, ept.endpoint_type)(msg_id)
        app.logger.warning(f"sending {message_type} {msg_id} {f_msg} -> {ept.endpoint_type} {ept.id}")  # NOQA
        ept.get_endpoint().send(f_msg)


@ce_app.task
def on_new_rockcore(rcm_id):
    """When a new message is received via the RockCorePushAPI, the
        corresponding RockStar is found or created.

        This task is effectively deprecated along with the use of RockStars
        within Paikea.

        This task handles message parsing and calls to endpoint_route as well.
        :param int rcm_id: id of source RockCorePushAPI message
    """
    source = "RockCoreAPI"
    msg_id = str(rcm_id)
    rcm = db.session.query(md.RockCorePushAPI).filter_by(id=rcm_id).one()

    try:
        rockstar = db.session.query(md.RockStar).filter_by(imei=rcm.imei).one()
    except NoResultFound:
        rockstar = md.RockStar(imei=rcm.imei,
                               serial=rcm.serial,
                               device_type=rcm.device_type)
        db.session.add(rockstar)
        try:
            db.session.commit()
        except Exception as e:
            print("Problem committing new RockStar: {}".format(rcm.serial))
            db.session.rollback()
            print(e)

    rs_id = rockstar.id

    # create a command message targetting a buoy

    if rcm.trigger == "MESSAGE":
        data = None
        payload = rcm.message
        try:
            data = parse_rockcore_payload(payload)
        except Exception as e:
            on_parsing_error(source, msg_id, "Payload parsing failed")
            print(e)
        if data:
            cmd = md.DeviceCommandMessage(
                command=data['command'],
                value=data['value'],
                source_msg_type='rockstar',
                source_msg_id=rcm_id,
                source_device_type='rockstar',
                source_device_id=rs_id)
            db.session.add(cmd)
            try:
                db.session.commit()
            except Exception as e:
                print("Problem adding DeviceCommand: {}".format(cmd))
                db.session.rollback()
                print(e)

            if cmd.id:
                send_to_endpoints(rs_id, 'rockstar', cmd.id, 'command')


@ce_app.task
def prepare_update_directory(upgrade_id):
    """ A Device Firmware Upgrade creates a directory to hold the firmware to
        be deployed and pulls hte firmware from git.

        If the passed upgrade_id does not correspond to a DeviceFirmwareUpgrade
        in the status "INIT", the steps will fail, as they are only valid for
        a new request.

        :param int upgrade_id: An id corresponding to a DeviceFirmwareUpgrade object
    """
    upgrade = db.session.query(md.DeviceFirmwareUpgrade).filter_by(id=upgrade_id).one()  # NOQA

    if upgrade.status != UpgradeStatus["INIT"]:
        print("fail")
        return

    device_id = upgrade.device_id
    device_type = upgrade.device_type
    # TODO: need to check if an upgrade is in progress for this device and fail
    # this if so
    if device_type == 'buoy':
        model = md.Buoy
    elif device_type == "handset":
        model = md.Handset

    try:
        device = db.session.query(model).filter_by(iam=device_id).one()
    except Exception as e:
        raise e

    # curr_version = device.firmware_version
    dev_name = device.iam
    # TODO: get the next update based on an upgrade path from this version
    # to next in the device specific version plan

    firmware_dir = app.config['FIRMWARE_BASE']
    firmware_repo = app.config['FIRMWARE_REPO']
    target_dir = f"{firmware_dir}/upgrades/{dev_name}"

    try:
        if os.listdir(target_dir):
            raise ValueError("Firmware directory not empty")
    except FileNotFoundError:
        os.mkdir(target_dir)

    ssh_cmd = 'ssh -i /home/paikea/.ssh/paikea-firmware-deploy'
    repo = git.Repo.clone_from(
        url=firmware_repo,
        to_path=target_dir,
        env={"GIT_SSH_COMMAND": ssh_cmd})

    repo.git.checkout('main')
    upgrade.status = UpgradeStatus["READY"]
    upgrade.root_dir = firmware_dir
    upgrade.file_path_suffix = f'upgrades/{dev_name}'
    db.session.add(upgrade)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    # switch to tag for target version
    # notify db that upgrade in progress
    # notify db that upgrade is ready


@ce_app.task
def clear_upgrade_directory(job_id):
    """ Cleans up the created files and directory from a firmware upgrade.

        :param int job_id: id of the specific DeviceFirmwareUpgrade to clean
    """
    upgrade = db.session.query(md.DeviceFirmwareUpgrade).filter_by(id=job_id).one()  # NOQA
    tree_to_remove = upgrade.root_dir + "/" + upgrade.file_path_suffix
    shutil.rmtree(tree_to_remove)
