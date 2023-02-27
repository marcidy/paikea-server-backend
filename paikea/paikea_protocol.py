"""
Functions for parsing messages core to the paikea system.
"""
import datetime
import binascii
from urllib.parse import unquote
import re


def parse_iridium_payload(raw_data):
    ''' Parse the hex encoded payload of an Iridium RockBlock API message.

        The expected format of the string:
        [$msg_type:]<key>:<value>[,<key>:<value>]*


        :param bytes raw_data: The data field of an iridium message
        :return: a dict with 'msg_type' as a string and 'fields' as a list.
        :rtype: dict
    '''
    data = binascii.unhexlify(raw_data.encode('ascii')).decode('ascii')

    # While I dislike doing data enrichment so early, this keeps a few bytes
    # out of the message protocol for now
    msg_type = re.match(r"^(PK[0-9]{3};)", data)
    if msg_type is None:
        raise ValueError(f"Missing Packet Type! {data}")
    else:
        data = data.replace(msg_type.group(), "")
        msg_type = msg_type.group()[0:-1]

    return {'msg_type': msg_type, 'fields': data.split(",")}


def convert_dd(dd):
    ''' Converts unsigned Decimal Degrees to deg, min, sec


        :param str dd: Coordinate in Decimal Degrees
        :return: {'deg': degrees, 'min': minutes, 'sec': seconds}
        :rtype: dict
    '''
    degs, mins = dd.split(".")
    d = int(degs)
    mins = float("0.{}".format(mins))
    m = int(60 * mins)
    s = 3600 * mins - 60 * m
    return {'deg': d, 'min': m, 'sec': s}


def convert_dms(d, m, s):
    ''' Converts Degrees, Minutes, and Seconds to unsigned Decimal Degrees

        :param int d: Degrees
        :param int m: Minutes
        :param float s: Seconds
        :rtype: dict
        :return: {'dd': value}
    '''
    return {'dd': d + m/60 + s/3600}


def convert_degdm(value):
    ''' Converts a NMEA GPS coordinate value to Degrees Decimal

    :param str value: [-][D]DD.MMmmmm formatted GPS coordinate
    :return: degrees decimal coordinate
    :rtype: float
    '''
    x, y = value.split(".")
    b = x[-2:]
    a = x[:-2]
    degs = int(a)
    dcms = float(b + "." + y)/60
    if degs >= 0:
        return degs + dcms
    if degs < 0:
        return degs - dcms


def convert_nmea(value):
    if value > 0:
        return round((value // 1) * 100 + (value % 1) * 60, 4)
    else:
        return -round(((abs(value) // 1) * 100 + (abs(value) % 1) * 60),4)


def buoy_time_to_datetime(timecode, transmit_date):
    ''' The timecode provided by the gps unit on the buoy is HMS.ssss,
        so we derive the year from the transmit date, provided by
        iridium.  Both are in UTC so no offsetting required.
        If a message is sent at 23:59:59, the transmit date will be 1 day
        forward, so we adjust implied date for the timecode appropriately.

        From a purely technical perspective, the transmit time will always be after
        the timecode, as the timecode is retrieved from the GPS unit before being
        sent.  Theoretically there could be skew between the GPS code and the
        iridium code, but we have to assume that both constellations are
        reportinng accurate times.

        The skew between the GPS time code and the iridium timecode could be
        relatively large (mins to hours) due to satellite connectivity or even
        firmware issues on the buoy.  While we assume the firmware functions to
        spec, the skew is an indicator of a problem and therefore useful to track
        as a diagnostic.

        :param str timecode: a NMEA timecode in HHMMSS.ssss format
        :param datetime.datetime transmit_date: Datetime base for computing the NMEA date
        :return: UTC timestamp of Buoy fix
        :rtype: datetime.datetime
    '''
    hms, ms = timecode.split(".")
    h = int(timecode[0:2])
    m = int(timecode[2:4])
    s = int(hms[4:])
    micros = int(float('0.' + ms)*1000000)

    timecode_time = datetime.time(h, m, s, micros)
    transmit_time = transmit_date.time()

    # if the timecode time is greater thant the transmit time, backup one
    # calendar day.
    if timecode_time > transmit_time:
        timecode_date = transmit_date.date() - datetime.timedelta(days=1)
    else:
        timecode_date = transmit_date.date()

    dt = datetime.datetime(
        timecode_date.year,
        timecode_date.month,
        timecode_date.day,
        h, m, s, micros)

    tz = datetime.timezone(datetime.timedelta(0), name="Etc/UTC")
    dt = dt.replace(tzinfo=tz)
    if dt > transmit_date:
        raise ValueError("Transit date must be greater than Buoy GPS Timecode")
    return dt


def transmit_time_to_datetime(transmit):
    ''' Iridium transit is not iso format, so we add the century.
        If this is still running in in 2099, well, we might have a problem.
        The double call to unquote is required to fully decode the url encoded
        data, but needs to be investigated why a single call isn't sufficient.
        Unclear if iridium is double encoding or occuring on parsing the
        request.

        :param str transmit: Iridium timecode from received API call
        :return: UTC timestamp of Iridium transmit time
        :rtype: datetime.datetime
    '''
    # FIXME: get date and tzinfo from machine and manage the 2099-2100
    # roll-over properly.
    tz = datetime.timezone(datetime.timedelta(0), "Etc/UTC")
    dt = datetime.datetime.fromisoformat('20'+unquote(unquote(transmit)))
    dt = dt.replace(tzinfo=tz)
    return dt


def parse_rockcore_payload(payload):
    """ RockCore payloads are used with RockStar devices to send commands
    to buoys.  They needed to be human readable as well as easily machine
    parsable.

    :param str payload: A payload of a RockStar message
    :return: None or dict of {'comamnd': command, 'value': value}
    :rtype: dict
    """
    ird_pat = re.compile("^IRD update ([0-9]*) min")
    beacon_pat = re.compile("^Beacon ([a-zA-Z]*)")

    match = re.match(ird_pat, payload)
    if match:
        mins = int(match.groups()[0])
        return {'command': 'update',
                'value': "{}".format(mins)}

    match = re.match(beacon_pat, payload)
    if match:
        beacon = 'SENTINEL'
        arg = match.groups()[0]
        if arg.upper() == "ON":
            beacon = "ON"
        elif arg.upper() == "OFF":
            beacon = "OFF"
        if beacon == 'SENTINEL':
            return
        else:
            return {'command': 'beacon',
                    'value': beacon}

    return
