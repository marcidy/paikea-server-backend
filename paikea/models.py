import os
from datetime import datetime
import requests
from flask import current_app as app
import boto3
from paikea.extensions import db


class ReportingMixin:
    """ Mixin to track creation and logical deletion status for records
    """
    #: DateTime, defaults to utc timestamp of record creation
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    #: Boolean, logically delete record from table
    logical_del = db.Column(db.Boolean, default=False)


class RockBlockMessage(ReportingMixin, db.Model):
    """ Serialization of incoming Iridium API message from a RockBlock Modem
    """
    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: String(128), IMEI for rockblock modem
    imei = db.Column(db.String(128))
    #: String(32), device type as indicated by Iridium's API
    device_type = db.Column(db.String(32))
    #: String(64), serial id as assigned by Iridium
    serial = db.Column(db.String(64))
    #: Integer, Mobile Originated Message Sequence Number, assigned by device
    momsn = db.Column(db.Integer)
    #: String(64), Transmit time from iridium network (UTC)
    transmit_time = db.Column(db.String(64))
    #: String(32), latitude of Iridium satelite
    iridium_latitude = db.Column(db.String(32))
    #: String(32), longitude of Iridium satelite
    iridium_longitude = db.Column(db.String(32))
    #: String(32), Circular Error of probability from Iridium Satelite location
    iridium_cep = db.Column(db.String(32))
    #: String(128), Iridium session status
    iridium_session_status = db.Column(db.String(128))
    #: String(1024) Iridium message payload
    data = db.Column(db.String(1024))
    #: Relationship to RockBlock Message Status table
    status = db.relationship("RBMessageStatus", uselist=False,
                             back_populates='rbm')
    #: Integer, Foreign Key to RockBlock Modem table
    rb_id = db.Column(db.Integer, db.ForeignKey('rock_block_modem.id'))
    #: Relationship to RockBlockModem for this message
    rb = db.relationship("RockBlockModem", back_populates='msgs')

    def to_dict(self):
        """Used to filter the serialization to a dict, but should be migrated
        to a Marshmallow"""
        stuff = ['imei', 'serial', 'momsn', 'transmit_time',
                 'iridium_latitude', 'iridium_longitude', 'iridium_cep',
                 'iridium_session_status', 'data']
        return {item: getattr(self, item) for item in stuff}


class RBMessageStatus(ReportingMixin, db.Model):
    """ Status table to track the processing of an incoming RockBlockMessage.
    This status table is used rather than updating the RockBlockMessage record.
    """
    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: Integer, Foreign Key linking this status to a RockBlockMessage
    rbm_id = db.Column(db.Integer, db.ForeignKey('rock_block_message.id'))
    #: String(128), status indicator
    status = db.Column(db.String(128))

    #: Relationship to RockBlockMessage
    rbm = db.relationship("RockBlockMessage",
                          back_populates='status')


class RockBlockModem(ReportingMixin, db.Model):
    """ A RockBlockModem has an associated list of messages delivered via
    the Iridium API.  It is associated with a device such as a handset or
    a buoy.
    """
    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: String(128) Modem IMEI as assigned by Iridium
    imei = db.Column(db.String(128))
    #: String(32), iridium device type, assigned by Iridium
    modem_type = db.Column(db.String(32))
    #: String(64), Iridium assigned serial for Modem
    serial = db.Column(db.String(64))
    #: Integer, Mobile Originated Message Sequence Number
    momsn = db.Column(db.Integer)
    #: String(64) Modem Status
    status = db.Column(db.String(64))
    #: Relationship to Messages send from this modem to the server
    msgs = db.relationship("RockBlockMessage")
    #: Integer, ID of linked device
    device_id = db.Column(db.Integer)
    #: String(32), device type to which this modem is associated,
    #: e.g. buoy or handset
    device_type = db.Column(db.String(32))

    def send(self, enc_msg):
        """ Send a message to this modem via the RockBlock API.  Message is
        sent as-is and therefore should be already encoded

        :param enc_msg: message to be sent hex encoded
        :type enc_msg: bytes
        """

        url = "https://core.rock7.com/rockblock/MT"
        user = os.environ.get("ROCKBLOCK_USER")
        pwrd = os.environ.get("ROCKBLOCK_PASS")
        if not user or not pwrd:
            raise ValueError("Missing RB Credentials, is environ set?")

        # enc_msg = binascii.hexlify(msg.encode('ascii')).decode('ascii')
        data = {'imei': self.imei,
                'data': enc_msg,
                'username': user,
                'password': pwrd}
        resp = None
        try:
            app.logger.warning(f"sending {enc_msg} to {url}")
            resp = requests.post(url, data)
        except Exception as e:
            print(f"RB message to {self.imei} failed")
            raise e
        else:
            print(f"Response: {resp}")


class Buoy(ReportingMixin, db.Model):
    """A Buoy has a RockBlockModem, from which messages are received and
    commands are sent.
    """

    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: String(16), firmware version of ESP32 in Buoy
    firmware_version = db.Column(db.String(16))
    #: String(16), Server ID for Buoy
    iam = db.Column(db.String(16))
    #: Integer, Foreign Key to RockBlockModem by modem ID.
    rb_id = db.Column(db.Integer, db.ForeignKey('rock_block_modem.id'))
    #: Relationship to RockBlockModem table
    rb = db.relationship("RockBlockModem",
                         uselist=False)
    #: String(64), status of Buoy (live, deactivated, etc)
    status = db.Column(db.String(64))


class Handset(ReportingMixin, db.Model):
    """ A Handset has a RockBlockModem, from which commands and messages are
    received and messages are sent
    """

    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: String(16), firmware version of ESP32 in Hanset
    firmware_version = db.Column(db.String(16))
    #: String(16), server device ID
    iam = db.Column(db.String(16))
    #: Integer, Foreign Key to RockBlockModem by modem ID
    rb_id = db.Column(db.Integer, db.ForeignKey('rock_block_modem.id'))
    #: Relationship to RockBlockModem table
    rb = db.relationship("RockBlockModem",
                         uselist=False)
    #: String(64), status of device (live, deactivated, etc)
    status = db.Column(db.String(64))


class PK001(ReportingMixin, db.Model):
    ''' Result of a parsed incoming PK001 message.
    Device 4D Location and battery

    example: PK001,3765.7897,N,12223.46653,W,193454.123,3.2
    '''
    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: Integer, Foreign Key to source RockBlockMessage
    rbm_id = db.Column(db.Integer, db.ForeignKey('rock_block_message.id'))
    #: DateTime, Transmit time as recorded by Iridium constellation, UTC
    ird_transmit_time = db.Column(db.DateTime)
    #: Numeric(9, 6), Latitude of the receiving Iridium Satellite
    ird_latitude = db.Column(db.Numeric(precision=9, scale=6))
    #: Numeric(9, 6), Longitude of receiving Iridium Satellite
    ird_longitude = db.Column(db.Numeric(precision=9, scale=6))
    #: Float, Circular Error of Probability of Iridium Satellite location
    ird_cep = db.Column(db.Float)
    #: Datetime, device fix timestamp, UTC
    device_transmit_time = db.Column(db.DateTime)
    #: Numeric(9, 6), Device latitude provided by onboard GPS
    device_latitude = db.Column(db.Numeric(precision=9, scale=6))
    #: Numeric(9, 6), Device longitude provided by onboard GPS
    device_longitude = db.Column(db.Numeric(precision=9, scale=6))
    #: String(1), Lattitude North/South indicator
    device_NS = db.Column(db.String(1))
    #: String(1), Longitude East/West indicator
    device_EW = db.Column(db.String(1))
    #: Float, raw battery voltage, uncalibrated
    device_batt = db.Column(db.Float)
    #: Float, device course over ground
    device_cog = db.Column(db.Float)
    #: Float, device speed over ground
    device_sog = db.Column(db.Float)
    #: Integer, device status flags
    device_status = db.Column(db.Integer)


class PK004(ReportingMixin, db.Model):
    ''' Result of a parsed incoming PK004 message.
    Device Position and velocity message

    example: PK004,3765.7897,N,12223.46653,W,2,18.3,193454.123

    '''
    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: Integer, Foreign Key linking this record to source Rock Block Message
    rbm_id = db.Column(db.Integer, db.ForeignKey('rock_block_message.id'))
    #: Float, device latitude in degrees decimal
    lat = db.Column(db.Float, nullable=False)
    #: String(1), North/South indicator for device latitude
    ns = db.Column(db.String(1), nullable=False)
    #: Float, device longitude in decimal degrees
    lon = db.Column(db.Float, nullable=False)
    #: String(1), East/West indicator for device longitdy
    ew = db.Column(db.String(1), nullable=False)
    #: Float, device speed over ground
    sog = db.Column(db.Float, nullable=False)
    #: Float, device course over ground (degrees clockwise from True North)
    cog = db.Column(db.Float, nullable=False)
    #: DateTime, Date and time of device position readings
    utc = db.Column(db.DateTime, nullable=False)


class MessageParsingError(ReportingMixin, db.Model):
    ''' A MessageParsingError is inserted when there is some issue in the
    automated processing of an incoming message.
    '''
    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: String(256) source of message, such as Iridium network
    msg_source = db.Column(db.String(256))
    #: String(256), ID of message
    msg_id = db.Column(db.String(256))
    #: String(256) error raised during processing
    error = db.Column(db.String(256))
    #: String(256), status of the error message
    error_status = db.Column(db.String(256))


class RockCorePushAPI(ReportingMixin, db.Model):
    ''' Mapping to db for RockStarMessage

    Specification per:
    https://docs.rock7.com/reference#push-api.

    Was required for RockStar devices which are no longer expected to
    be used.
    '''
    id = db.Column(db.String(256), primary_key=True)
    at = db.Column(db.String(32))
    transport = db.Column(db.String(32))
    imei = db.Column(db.String(128),
                     db.ForeignKey('rock_star.imei'),
                     nullable=False)
    # imei = db.Column(db.String(32))
    device_type = db.Column(db.String(32))
    serial = db.Column(db.Integer)
    momsn = db.Column(db.Integer)
    txAt = db.Column(db.String(64))
    gps_time = db.Column(db.String(64))
    iridium_longitude = db.Column(db.Float)
    iridium_latitude = db.Column(db.Float)
    cep = db.Column(db.Float)
    trigger = db.Column(db.String(32))
    source = db.Column(db.String(32))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    sog = db.Column(db.Float)  # knots
    cog = db.Column(db.Float)
    alt = db.Column(db.Float)  # meters
    temp = db.Column(db.Integer)
    battery = db.Column(db.Integer)
    power = db.Column(db.Boolean)
    message = db.Column(db.String(256))
    ack_request = db.Column(db.Boolean)
    message_ack = db.Column(db.Integer)
    alert = db.Column(db.Boolean)
    waypoint = db.Column(db.String(32))
    app_msg_addr = db.Column(db.String(256))
    app_msg_content = db.Column(db.String(256))
    beacons = db.Column(db.String(256))
    ext_ref = db.Column(db.String(64))
    averageCog = db.Column(db.Float)
    averageSog = db.Column(db.Float)
    pdop = db.Column(db.Float)
    transmit_time = db.Column(db.String(32))
    rockstar = db.relationship("RockStar", back_populates='msgs')


class RockStar(ReportingMixin, db.Model):
    ''' A RockStar is an Iridium device which was to be used as a handset.
    It has since been deprecated, as is this table '''

    id = db.Column(db.Integer, primary_key=True)
    imei = db.Column(db.String(128), unique=True, nullable=False)
    device_type = db.Column(db.String(32), nullable=False)
    serial = db.Column(db.String(64), nullable=False)
    msgs = db.relationship("RockCorePushAPI")

    def send(self, msg):
        url = "https://core.rock7.com/API2/SendMessage/"
        user = os.environ.get('ROCKCORE_USER')
        pwrd = os.environ.get('ROCKCORE_PASS')

        if not user or not pwrd:
            raise ValueError("Missing RockCore credentials!")

        params = {
            'username': user,
            'password': pwrd,
            'message': msg, }
        url += self.serial

        app.logger.warning(f"sending {msg} to rockstar: {self.serial}")
        reponse = requests.post(url, params=params)
        print(f"Response: {reponse}")


class SQS_Endpoint(ReportingMixin, db.Model):
    ''' The name and url of an AWS SQS queue '''
    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: Label of the queue
    queue_name = db.Column(db.String(128), nullable=False)
    #: URL of the SQS queue
    url = db.Column(db.String(128), nullable=False)

    def get_queue(self):
        ''' Retrieves the AWS boto3 queue representation for this record'''
        for queue in boto3.resource('sqs').queues.all():
            if self.url == queue.url:
                return queue
        print(f"SQS queue not accessible: {self.queue_name}")

    def send(self, msg):
        ''' Attempts to send the msg to the AWS SQS queue using boto3.

        Credentails are handled via boto3's usual methods and not explicitly
        by this function.

        :param msg: The formatted message to send as the MessageBody
        '''
        queue = self.get_queue()
        if queue:
            try:
                app.logger.warning(f"sending {msg} to SQS {self.queue_name}")
                queue.send_message(MessageBody=msg)
            except Exception as e:
                print(f"Problem sending to SQS queue: {queue}")
                raise e
        else:
            print(f"Problem finding queue for SQS_Endpoing: {self.id}")


class DeviceCommandMessage(ReportingMixin, db.Model):
    ''' An automated command sent to a device '''
    #: Integer, Primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: String(64), Command name
    command = db.Column(db.String(64), nullable=False)
    #: String(64), Command value
    value = db.Column(db.String(64), nullable=False)
    #: String(64), Type of source message which triggered this command
    source_msg_type = db.Column(db.String(64), nullable=False)
    #: Integer, ID of message which triggered this command
    source_msg_id = db.Column(db.Integer, nullable=False)
    #: String(64) Type of device which sent the message which triggered
    #: this comamnd
    source_device_type = db.Column(db.String(64), nullable=False)
    #: Integer, ID of device which sent the message which triggered
    #: this command
    source_device_id = db.Column(db.Integer, nullable=False)


class EndpointRoute(ReportingMixin, db.Model):
    ''' Maps source devices to enpoints to which messages are delivered.

    Every message source has a type, every message has a type, and every
    destination has an ID and a type.  Based on this information, messages
    are routed from sources to destinations, through destination specific
    formatting.

    '''
    #: Integer, Primary Key for route
    id = db.Column(db.Integer, primary_key=True)
    #: String(64) Type of message source, ie buoy, handset, rockstar, etc
    source_device_type = db.Column(db.String(64), nullable=False)
    #: Integer, ID of source device to find device in source table
    source_device = db.Column(db.Integer, nullable=False)
    #: String(64), Message type, i.e. PK001, PK004, etc
    msg_type = db.Column(db.String(64), nullable=False)
    #: String(64), Type of endpoint, i.e. SQS queue or device type
    endpoint_type = db.Column(db.String(64), nullable=False)
    #: Integer, id of endpoint in endpoint or device specific table
    endpoint_id = db.Column(db.Integer, nullable=False)
    #: Boolean, route is currently enabled or not
    enabled = db.Column(db.Boolean, nullable=False, default=True)

    #: Allowed device types
    source_device_types = [
        'buoy',
        'handset',
        'rockstar', ]
    #: Mapping for endpoint types to table objects
    endpoint_types = {
        'sqs': SQS_Endpoint,
        'handset': RockBlockModem,
        'buoy': RockBlockModem,
        'rockstar': RockStar}

    def get_endpoint(self):
        ''' Retrieve the endpoint object associated with this route'''
        return db.session.query(self.endpoint_types[self.endpoint_type]).\
            filter_by(id=self.endpoint_id).one()

    def get_source(self):
        ''' Retrieve source object associated with this route'''
        return db.session.query(self.endpoint_types[self.source_device_type]).\
            filter_by(id=self.source_device).one()


class DeviceFirmwareUpgrade(ReportingMixin, db.Model):
    ''' Record of an attempted firmware updated for a device.  When an
    Upgrade is initiated, the status, path to the files, and target device
    are persisted in this record.  The status is updated through the lifecycle
    of the device upgrade.
    '''
    #: Integer, primary Key
    id = db.Column(db.Integer, primary_key=True)
    #: String(16), device type i.e. buoy, handset, etc.
    device_type = db.Column(db.String(16), nullable=False)
    #: String(32), device identifier
    device_id = db.Column(db.String(32), nullable=False)
    #: Integer, status of the upgrade
    status = db.Column(db.Integer, nullable=False)
    #: String(128), root directory for the files
    root_dir = db.Column(db.String(128))
    #: String(128), path suffix off root_dir for update specific files
    file_path_suffix = db.Column(db.String(128))

    def full_path(self):
        ''' Full path to the upgrade files'''
        return f"{self.root_dir}/{self.file_path_suffix}"
