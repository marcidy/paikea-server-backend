from flask import (
    current_app as app,
    Blueprint,
    render_template,
    request,
    make_response,
    send_from_directory,
    jsonify,
)
from flask_cors import CORS
from sqlalchemy.orm import exc
from sqlalchemy import(
    and_,
    or_,
)
from .extensions import db
from .models import (
    RockBlockMessage,
    RBMessageStatus,
    RockBlockModem,
    Buoy,
    PK001,
    MessageParsingError,
    RockStar,
    Handset,
    EndpointRoute,
    SQS_Endpoint,
)
from .routes import (
    check_route,
    check_route_for_participant,
)
from .utils import parse_req
import paikea.firmware as firmware
import paikea.serializers as ser
import paikea.tasks as tasks


json_endpoints_bp = Blueprint('json', __name__)
incoming_bp = Blueprint('incoming', __name__)
device_bp = Blueprint('device', __name__)
firmware_bp = Blueprint('firmware', __name__)
app_bp = Blueprint('router', __name__)

CORS(json_endpoints_bp)

blueprints = [
    json_endpoints_bp,
    incoming_bp,
    device_bp,
    firmware_bp,
    app_bp,
]


@incoming_bp.route('/rockstar/incoming', methods=['POST', 'GET'])
def rockstar_incoming():
    """ route: /rockstar/incoming

        Endpoint for incoming messages via a push from the RockCore service,
        used only for RockStar devices.  The result of a successful push will be
        a RockCoreAPI message persisted in the database, and a triggering of the
        "on_+new_rockcore" task.

        This must return 200 otherwise the same message will be continually
        pushed to the server by the RockCore service.
    """
    if request.method == "POST":
        try:
            data = request.get_json()
        except Exception as e:
            print("Request JSON not available")
            print(data)
            raise e

        if 'JWT' in data:
            jwt = data.pop('JWT')  # NOQA
            # FIXME: validate JWT wtih pubkey from rock core

        rock_core_schema = ser.RockCorePushAPI()
        msg = None
        try:
            msg = rock_core_schema.load(data, session=db.session)
        except Exception as e:
            print(e)
            print("RockCore API deserialization failed!")
            print(data)
            raise e

        if msg:
            db.session.add(msg)
            try:
                db.session.commit()
            except Exception as e:
                print("Committing failed!")
                print(msg)
                db.session.rollback()
                raise e

            tasks.on_new_rockcore.delay(msg.id)

        return make_response("OK", 200)


@incoming_bp.route("/rockblock/incoming", methods=['POST', 'GET'])
def raw():
    """ route: /rockblock/incoming
        Endpoint for Iridium RockBlock push messages.  Persists the message
        data and triggers the on_new_rbm task to process the message.
    """
    if request.method == "POST":
        request_data = request.get_data()
        print(request_data)
        data = parse_req(request_data)
        app.logger.info("Request data: {}".format(request_data))

        rbm = RockBlockMessage(**data)
        db.session.add(rbm)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.error("Incoming message commit failed: {}".format(rbm))

        rbm_status = RBMessageStatus(rbm_id=rbm.id, status='new')
        db.session.add(rbm_status)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            err_msg = "Incomming Message status update failed: {}"
            app.logger.error(err_msg.format(rbm_status))

        tasks.on_new_rbm.delay(rbm.id)
        return make_response("OK", 200)

    if request.method == "GET":
        messages = db.session.query(RockBlockMessage).all()
        return render_template('raw_messages.html',
                               title='Messages',
                               messages=messages)


@json_endpoints_bp.route("/json/messages", methods=['GET', ])
def json_messages():
    messages = db.session.query(RockBlockMessage).\
        filter(RockBlockMessage.logical_del is False).all()[-10:]
    msg_schema = ser.RockBlockMessageSchema(many=True)
    return msg_schema.jsonify(messages)


@json_endpoints_bp.route("/v1/rockblocks", methods=['GET', ])
def rb_modem():
    """ route: /v1/rockblocks

        Access a list of RockBlock modems
    """
    modem_schema = ser.RBModemSchema(many=True)
    if request.method == "GET":
        modems = db.session.query(RockBlockModem).all()
        return modem_schema.jsonify(modems)


@json_endpoints_bp.route("/v1/buoys", methods=['GET', ])
def all_buoy():
    """ route: /v1/buoys

        Access json list of buoys
    """
    buoy_schema = ser.BuoySchema(many=True)
    if request.method == "GET":
        buoys = db.session.query(Buoy).all()
        return buoy_schema.jsonify(buoys)


@json_endpoints_bp.route("/v1/buoys/<buoy_id>", methods=["GET", ])
def single_buoy(buoy_id):
    """ route: /v1/buoys/<buoy_id>

        Access a specific buoy by ID.

        :param int buoy_id: id of buoy to access
    """
    buoy_schema = ser.BuoySchema()
    buoy = db.session.query(Buoy).filter(id=buoy_id).one()
    return buoy_schema.jsonify(buoy)


@json_endpoints_bp.route("/v1/buoys/create", methods=["POST", ])
def add_new_buoy():
    """ route: /v1/buoys/create

        Create a new buoy linked to a modem
    """
    data = request.get_json();

    iam = data.get('iam')
    modem_id = data.get('modem')
    fail = False
    errors = []

    if not iam:
        fail = True
        errors.append("Missing Buoy label")

    if db.session.query(Buoy).filter_by(iam=iam).all():
        fail = True
        errors.append("Buoy with iam {} already exists".format(iam))

    if not modem_id:
        fail = True
        errors.append("Missing Modem")

    rb = None
    try:
        rb = db.session.query(RockBlockModem).filter_by(id=modem_id).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        errors.append("Bad modem ID: {}".format(modem_id))
        fail = True

    if rb:
        if rb.device_type:
            errors.append("Modem {} already linked".format(modem_id))
            fail = True

    if not fail:
        rb.device_type = 'buoy'

        buoy = Buoy(iam=iam, rb=rb)

        db.session.add(buoy)
        db.session.add(rb)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            errors.append("Problem committing")
            fail = True

    if fail:
        return make_response(jsonify(errors), 500)
        # create response with errors and display them
    else:
        return make_response("OK", 200)


@json_endpoints_bp.route("/v1/handsets/create", methods=["POST", ])
def add_new_handset():
    """ route: /v1/handset/create

        Create a new handset linked to a modem
    """
    data = request.get_json();

    iam = data.get('iam')
    modem_id = data.get('modem')
    fail = False
    errors = []

    if not iam:
        fail = True
        errors.append("Missing Handset label")

    if db.session.query(Handset).filter_by(iam=iam).all():
        fail = True
        errors.append("Handset with iam {} already exists".format(iam))

    if not modem_id:
        fail = True
        errors.append("Missing Modem")

    rb = None
    try:
        rb = db.session.query(RockBlockModem).filter_by(id=modem_id).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        errors.append("Bad modem ID: {}".format(modem_id))
        fail = True

    if rb:
        if rb.device_type:
            errors.append("Modem {} already linked".format(modem_id))
            fail = True

    if not fail:
        rb.device_type = 'handset'

        handset = Handset(iam=iam, rb=rb)

        db.session.add(handset)
        db.session.add(rb)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            errors.append("Problem committing")
            fail = True

    if fail:
        # create response with errors and display them
        return make_response(jsonify(errors), 500)
    else:
        return make_response("OK", 200)


@json_endpoints_bp.route('/v1/<link_type>s/link', methods=["POST", ])
def link_device(link_type):
    data = request.json

    dev_id= data.get('id')
    modem_id = data.get('modem')
    errors = []

    if link_type not in ['handset', 'buoy']:
        errors.append(f"Cannot attempt link of type {link_type}")

    if link_type == 'handset':
        model = Handset
    if link_type == 'buoy':
        model = Buoy

    if not dev_id:
        errors.append(f"Missing {link_type} ID")

    if not modem_id:
        errors.append("Missing Modem ID")

    if errors:
        return make_response(jsonify({'errors': errors}), 500)

    device = None
    try:
        device = db.session.query(model).filter_by(id=dev_id).one()
    except exc.MultipleResultsFound:
        errors.append(f"Multiple results for {dev_id} found")
    except exc.NoResultFound:
        errors.append(f"No {link_type} {dev_id} exists")

    rb = None
    try:
        rb = db.session.query(RockBlockModem).filter_by(id=modem_id).one()
    except exc.MultipleResultsFound:
        errors.append(f"Multiple results for {modem_id} found")
    except exc.NoResultFound:
        errors.append(f"No Modem with id {modem_id} exists")

    if errors:
        return make_response(jsonify({'errors': errors}), 500)

    if device and rb:
        rb.device_type = link_type
        device.rb = rb

        db.session.add(device)
        db.session.add(rb)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            errors.append("Problem committing link")

    else:
        errors.append("Server Error: missing device(s)")

    if errors:
        return make_response(jsonify({'errors': errors}), 500)
    else:
        return make_response("OK", 200)



@json_endpoints_bp.route("/v1/<link_type>s/unlink", methods=["POST", ])
def unlink_device(link_type):
    data = request.json
    dev_id = data['id']

    route_q = db.session.query(EndpointRoute)
    errors = []

    if link_type not in ['handset', 'buoy', 'route']:
        errors.append(f"{link_type} is not a valid device")

    if not dev_id:
        errors.append("No useful id included to unlink")

    if link_type == 'handset':
        model = Handset
    elif link_type == 'buoy':
        model = Buoy

    device = None
    try:
        device = db.session.query(model).filter_by(id=dev_id).one()
    except exc.NoResultFound:
        errors.append(f"No {link_type} found with id {dev_id}.")
    except exc.MultipleResultsFound:
        errors.append(f"Multiple devices of type {link_type} with id {dev_id}.")

    if errors:
        return make_reponse(jsonify({'errors': errors}), 500)

    modem_id = device.rb_id
    modem = device.rb
    if not modem_id:
        errors.append(f"No modem attached to {link_type} {dev_id}.")
        return make_reponse(jsonify({'errors': errors}), 500)

    if link_type in ['handset', 'buoy']:
        routes = route_q.filter(
            or_(
                and_(
                    EndpointRoute.source_device_type == link_type,
                    EndpointRoute.source_device == modem_id
                ),
                and_(
                    EndpointRoute.endpoint_type == link_type,
                    EndpointRoute.endpoint_id == modem_id
            ))).all()

        errors.extend( [f"Device {modem_id} used in route {r.id}"
                        for r in routes] )

    if errors:
        return make_response(jsonify({'errors': errors}), 500)

    if modem.device_type != link_type:
        errors.append(f"Modem has wrong device type")
        return make_response(jsonify({'errors': errors}), 500)

    modem.device_type = ''
    modem.device_id = None
    device.rb = None
    db.session.add(modem)
    db.session.add(device)

    try:
        db.session.flush()
        db.session.commit()
    except Exception:
        db.session.rollback()
        errors.append("Could not commit removals")
        return make_response({'errors': errors}, 500)

    return make_response({'errors': errors}, 200)


@json_endpoints_bp.route("/v1//buoys/<buoy_id>/messages", methods=["GET", ])
def buoy_messages(buoy_id):
    """ route: /v1/buoys/<buoy_id>/messages

        Access json list of messages associated with a buoy

        :param int buoy_id: id of buoy
    """
    buoy = db.session.query(Buoy).filter(id=buoy_id).one()
    msg_schema = ser.PK001Schema(many=True)
    msgs = db.session.query(PK001).filter(rbm_id=buoy.rbm_id).all()
    return msg_schema.jsonify(msgs)


@json_endpoints_bp.route("/v1/errors", methods=["GET", ])
def errors():
    """ route: /v1/errors

        Access json list of unhandled error message paring errors
    """
    errors = db.session.query(MessageParsingError).all()
    schema = ser.MessageParsingErrorSchema(many=True)
    return schema.jsonify(errors)


@json_endpoints_bp.route("/v1/rockstars", methods=["GET", ])
def rockstars():
    """ route: /v1/rockstars

        Access json list of Rockstar devices
    """
    devices = db.session.query(RockStar).all()
    schema = ser.RockStarSchema(many=True)
    return schema.jsonify(devices)


@json_endpoints_bp.route("/v1/handsets", methods=["GET", ])
def handsets():
    """ route: /v1/handsets

        Access json list of handsets
    """
    handsets = db.session.query(Handset).all()
    schema = ser.HandsetSchema(many=True)
    return schema.jsonify(handsets)


@json_endpoints_bp.route("/v1/<device_type>s/delete", methods=["POST", ])
def delete_device(device_type):
    data = request.json
    dev_id = data.get('id')
    device = None
    errors = []

    if not dev_id:
        errors.append("Missing Device ID.")

    if device_type == 'handset':
        model = Handset
    elif device_type == 'buoy':
        model = Buoy
    else:
        errors.append(f"Cannot delete {device_type} from this interface.")
        return make_response(jsonify({'errors': errors}), 500)

    try:
        device = db.session.query(model).filter_by(id=dev_id).one()
    except exc.NoResultFound:
        errors.append(f"No such device: {dev_id}")
    except exc.MultipleResultsFound:
        errors.append(f"Multiple devices found for {dev_id}.")

    if device.rb:
        errors.append(f"Device {dev_id} still linked. Abort.")

    if errors:
        return make_response(jsonify({'errors': errors}), 500)

    db.session.delete(device)
    try:
        db.session.commit()
    except Exception:
        errors.append(f"Could not commit change to device {dev_id}.  Abort.")
        return make_response(jsonify({'errors': errors}), 500)

    return make_response("OK", 200)


@device_bp.route("/v1/test/<path:path>", methods=["GET", ])
def firmware_test(path):
    return send_from_directory('firmware', path)


@device_bp.route("/v1/buoy/register", methods=["POST", ])
def register_buoy():
    """ route: /v1/buoy/register

        Register a new buoy device

        Requires json data in POST request.

        Creates a new Buoy record and returns a json object with
        assigned device id as the 'iam' parameter
    """
    data = request.get_json()

    if "iam" in data:
        devices = db.session.query(Buoy).filter_by(iam=data['iam']).all()

        if len(devices) == 1:
            return jsonify({'iam': devices[0].iam})

        elif len(devices) > 1:
            raise ValueError(f"Too many devices for {data['iam']}")

    if "iam" not in data or len(devices) == 0:
        buoy = Buoy()
        db.session.add(buoy)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        buoy.iam = f"PK{buoy.id:03}"

        db.session.add(buoy)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        return jsonify({'iam': buoy.iam})


@device_bp.route("/v1/handset/register", methods=["POST", ])
def register_handset():
    """ route: /v1/handset/register

        Register a new handset device with a POST request.

        Adds a new Handset record and returns a json object with the
        device id as the "iam" parameter.
    """
    data = request.get_json()

    if 'iam' in data:
        devices = db.session.query(Handset).filter_by(iam=data['iam']).all()

        if len(devices) == 1:
            return jsonify({'iam': devices[0].iam})

        elif len(devices) > 1:
            raise ValueError(f"Too many devices for {data['iam']}")

    if 'iam' not in data or len(devices) == 0:
        handset = Handset()
        db.session.add(handset)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        handset.iam = f"HS{handset.id:03}"

        db.session.add(handset)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    return jsonify({'iam': handset.iam})


@device_bp.route("/v1/device/<iam>", methods=["GET", ])
def handset(iam):
    """ route: /v1/device/<iam>

        Access a device page and connect a websocket to the device.

        :param string iam: device unique iam identifier
    """
    return render_template('device.htm', iam=iam)


@firmware_bp.route('/v1/<device_type>/<device_id>/upgrade',
                   methods=["GET", "POST"])
def firmware_upgrade_request(device_type, device_id):
    """ route: /v1/<device_type>/<device_id>/upgrade

        Handle upgrade related tasks.

        :param str device_type: Type of device requesting upgrade
        :param str device_id: Unique id of device requestiong upgrade
    """
    data = request.get_json()
    data['device_type'] = device_type
    data['device_id'] = device_id
    vals = firmware.handle_upgrade_req(data)
    if data['cmd'] == 'get_file':
        return send_from_directory('../firmware',
                                   vals['path'],
                                   mimetype="text/plain",
                                   as_attachment=True)
    else:
        return jsonify(vals)


@json_endpoints_bp.route("/v1/routing", methods=["GET"])
def routing_table():

    table = db.session.query(EndpointRoute).all()
    schema = ser.EndpointRouterSchema(many=True)
    return schema.jsonify(table)


@json_endpoints_bp.route("/v1/routing/create", methods=["POST"])
def add_new_route():

    data = request.get_json()
    errors = check_route(data)

    if errors:
        return make_response(jsonify(errors), 500)

    try:
        new_route = EndpointRoute(
            source_device_type=data['source']['type'],
            source_device=data['source']['id'],
            msg_type=data['source']['msg'],
            endpoint_type=data['target']['type'],
            endpoint_id=data['target']['id'],
            enabled=data['enabled'])
    except Exception as e:
        errors.append('Failed to create new Route')
        errors.append(f"{e}")
        return make_response(jsonify(errors), 500)

    db.session.add(new_route)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return make_response(jsonify(['Failed to insert new Route']), 500)
    return make_response("OK", 200)


@json_endpoints_bp.route("/v1/routing/delete", methods=["POST"])
def delete_route():
    data = request.json
    route_id = data.get('id')
    errors = []

    if not route_id:
        errors.append("No Route ID sent")

    route = None
    try:
        route = db.session.query(EndpointRoute).filter_by(id=route_id).one()
    except exc.MultipleResultsFound:
        errors.append(f"Multiple routes for ID {route_id} found.")
    except exc.NoResultFound:
        errors.append(f"No route for ID {route_id} found.")

    if errors:
        return make_response(jsonify({'errors': errors}), 500)

    db.session.delete(route)
    try:
        db.session.commit()
    except Exception:
        errors.append("Error committing change, abort")

    if errors:
        return make_response(jsonify({'errors': errors}), 500)
    else:
        return make_response("OK", 200)


@json_endpoints_bp.route("/v1/routing/enable", methods=["POST"])
def disenable_route():
    data = request.json
    errors = []

    rid = data.get('id')
    enable = data.get('enable')
    if not rid:
        errors.append("No route ID given.")
    if enable is None:
        errors.append("No enable data given.")

    route = None
    try:
        route = db.session.query(EndpointRoute).filter_by(id=rid).one()
    except exc.NoResultFound:
        errors.append(f"No route for id {rid}")
    except exc.MultipleResultsFound:
        errors.append(f"Multiple routes for id {rid}.  Abort.")

    if errors:
        return make_response(jsonify({'errors': errors}), 500)

    route.enabled = enable
    db.session.add(route)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        errors.append(f"Could not commit data to database")
        make_response(jsonify({'errors': errors}), 500)

    return make_response("OK", 200)


@json_endpoints_bp.route("/v1/queues", methods=["GET"])
def sqs_queues():
    data = db.session.query(SQS_Endpoint).all()
    schema = ser.SQSEndpointSchema(many=True)
    return schema.jsonify(data)


@app_bp.route("/v1/app", methods=['GET', 'POST'])
def routes():
    return render_template('app.htm')
