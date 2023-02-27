import pytest
from paikea.paikea_protocol import (
    parse_iridium_payload,
    convert_dd,
    convert_dms,
    convert_degdm,
    buoy_time_to_datetime,
    transmit_time_to_datetime,
)
import datetime


def test_parse_iridium_payload():
    test_case = '504b3030313b6c61743a333734392e353037342c4e533a4e2c6c6f6e3a31323231362e363032312c45573a572c7574633a3033303530312e3038362c626174743a342e37'
    parsed = parse_iridium_payload(test_case)
    msg_type = parsed.pop("msg_type")
    fields = parsed.pop("fields")
    out = {"msg_type": msg_type}
    for item in fields:
        k, v = item.split(":")
        out[k] = v

    assert out['msg_type'] == "PK001"
    assert out['lat'] == '3749.5074'
    assert out['NS'] == "N"
    assert out['lon'] == '12216.6021'
    assert out['EW'] == 'W'
    assert out['utc'] == '030501.086'
    assert out['batt'] == '4.7'


def test_convert_degdm():
    test_case = '3749.5075'
    out = convert_degdm(test_case)
    assert out == 37.825125

    test_case = '12216.6023'
    out = convert_degdm(test_case)
    assert out == 122.276705


def test_parse_iridium_payload_notype():
    test_case = '3b6c61743a3130302c6c6f6e3a3230302c45573a572c4e533a4e2c7574633a3230303030302e3030303b'
    with pytest.raises(ValueError):
        parse_iridium_payload(test_case)


def test_convert_dd():
    d = convert_dd("30.263888889")
    assert d['deg'] == 30
    assert d['min'] == 15
    assert d['sec'] == pytest.approx(50)


def test_convert_dms():
    d = convert_dms(30, 15, 50)
    assert d['dd'] == pytest.approx(30.263888889)


def test_buoy_time_to_datetime():
    base_dt = datetime.datetime(2020, 1, 5, 12, 45, 22, 191919)
    tz = datetime.timezone(datetime.timedelta(0), name="Etc/UTC")
    base_dt = base_dt.replace(tzinfo=tz)

    for hh in range(24):
        for mm in range(60):
            for ss in range(60):
                buoy_time = buoy_time_to_datetime(
                    "{:02}{:02}{:02}.0000".format(hh, mm, ss),
                    base_dt)
                assert buoy_time <= base_dt
