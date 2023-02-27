import random
import binascii
import paikea.models as md


RBM_PKT = "{};{}"
PK001_PKT = "lat:{},NS:{},lon:{},EW:{},utc:{},batt:{},sog:{},cog:{},sta:{}"
# PKEA004,37.777,N,122.2346,W,2,18.3,193454.123;
PK004_PKT = "{},{},{},{},{},{},{}"


def random_location():

    lat = min(9000, round(random.randint(-9000, 9000) + random.random(), 5))
    lon = min(18000, round(random.randint(-18000, 18000) + random.random(), 5))
    utc = f"{random.randint(0, 24):02}" + \
        f"{random.randint(0,59):02}" + \
        f"{random.randint(0,59):02}" + \
        f"{round(random.random(), 4):04}"[1:]

    ns = "N"
    if lat < 0:
        ns = "S"

    ew = "E"
    if lon < 0:
        ew = "W"

    cog = f"{round(random.randint(0, 360) + random.random(), 1)}"
    sog = f"{round(random.randint(0, 25) + random.random(), 1)}"

    return {'lat': lat, 'lon': lon, 'utc': utc, 'ns': ns, 'ew': ew,
            'cog': cog, 'sog': sog}


def pk001(loc_data):
    pk001 = PK001_PKT.format(abs(loc_data['lat']),
                             loc_data['ns'],
                             abs(loc_data['lon']),
                             loc_data['ew'],
                             loc_data['utc'],
                             3.2,
                             loc_data['cog'],
                             loc_data['sog'],
                             4)
    pkt = RBM_PKT.format("PK001", pk001)
    return pkt


def pk004(loc_data):
    pk004 = PK004_PKT.format(
        abs(loc_data['lat']),
        loc_data['ns'],
        abs(loc_data['lon']),
        loc_data['ew'],
        loc_data['sog'],
        loc_data['cog'],
        loc_data['utc'])
    pkt = RBM_PKT.format("PK004", pk004)
    return pkt


def pk005(on=True):
    val = "1" if on else "0"
    return RBM_PKT.format("PK005", val)


def pk006(secs):
    return RBM_PKT.format("PK006", "{}".format(secs))


def random_rbm_data():
    pkt_select = random.randint(0, 1)
    loc_data = random_location()

    if pkt_select == 0:
        return pk001(loc_data)

    elif pkt_select == 1:
        return pk004(loc_data)


def single_test_rock_block_message(pkt_data):
    data = binascii.hexlify(pkt_data.encode("ascii")).decode("ascii")
    rbm = md.RockBlockMessage(
        imei="TESTIMEI1234",
        device_type="ROCKBLOCK",
        serial='13760',
        transmit_time='20-10-02%2021%3A07%3A37',
        iridium_latitude='37.7740',
        iridium_longitude='-122.4050',
        iridium_cep='4.0',
        iridium_session_status='2',
        data=data)
    return rbm


def rockblock_messages(num=10):
    imeis = [
        "ABC12345678",
        "12345678910",
        "987654CBA", ]
    device_types = ["ROCKBLOCK", ]
    serials = ['13760', '17458']

    transmit_times = [
        '20-10-02%2021%3A07%3A37',
        '20-10-02%2021%3A13%3A15',
        '20-10-02%2021%3A19%3A38',
        '20-10-02%2021%3A26%3A13',
        '20-10-02%2021%3A31%3A16',
        '20-10-02%2021%3A36%3A30',
        '20-09-21%2020%3A48%3A09',
        '20-09-21%2021%3A05%3A31',
        '20-09-24%2023%3A58%3A24',
        '20-09-25%2000%3A08%3A00',
    ]

    ird_lats = [
        '37.7740',
        '37.7694',
        '37.7380',
        '37.7672',
        '37.8153',
        '37.7858',
        '37.8192',
        '37.8310',
        '37.8310',
        '37.8265',
    ]

    ird_lons = [
        '-122.4050',
        '-121.6492',
        '-121.4855',
        '-122.3423',
        '-123.9421',
        '-122.3666',
        '-122.2655',
        '-122.2271',
        '-122.2271',
        '-121.8994',
    ]

    ird_ceps = [
        '4.0',
        '275.0',
        '95.0',
        '8.0',
        '162.0',
        '3.0',
        '2.0',
        '3.0',
        '11.0',
        '93.0',
    ]

    ird_sess_stat = [
        '0',
        '2',
    ]

    messages = []
    for x in range(num):
        rbm_data = binascii.hexlify(random_rbm_data().encode("ascii")).decode("ascii")
        messages.append(md.RockBlockMessage(
            imei=random.choice(imeis),
            device_type=random.choice(device_types),
            serial=random.choice(serials),
            momsn=random.randint(0, 1000),
            transmit_time=random.choice(transmit_times),
            iridium_latitude=random.choice(ird_lats),
            iridium_longitude=random.choice(ird_lons),
            iridium_cep=random.choice(ird_ceps),
            iridium_session_status=random.choice(ird_sess_stat),
            data=rbm_data))

    return messages
