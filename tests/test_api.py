from paikea import models as md


def test_add_bad_buoy(client):
    ep = '/v1/buoys/create'

    data = {'iam': '', 'modem': '1'}

    response = client.post(ep, json=data)
    errors = response.json

    assert errors
    assert response.status_code == 500

    exp_errors = [
        "Missing Buoy label",
        "Bad modem ID: 1",
    ]

    for err in exp_errors:
        assert err in errors

    data = {'iam': "TEST", 'modem': '' }
    response = client.post(ep, json=data)
    errors = response.json

    assert errors
    assert response.status_code == 500

    exp_errors = [
        "Missing Modem",
    ]

    for err in exp_errors:
        assert err in errors


def test_add_bad_handset(client):
    ep = '/v1/handsets/create'

    data = {'iam': '', 'modem': '1'}

    response = client.post(ep, json=data)
    errors = response.json

    assert errors
    assert response.status_code == 500

    exp_errors = [
        "Missing Handset label",
        "Bad modem ID: 1",
    ]

    for err in exp_errors:
        assert err in errors

    data = {'iam': "TEST", 'modem': '' }
    response = client.post(ep, json=data)
    errors = response.json

    assert errors
    assert response.status_code == 500

    exp_errors = [
        'Missing Modem',
    ]

    for err in exp_errors:
        assert err in errors


def test_link_buoy(create_modems, flask_app, database):

    db = database
    modems = create_modems
    ep = '/v1/buoys/create'

    assert not modems[0].device_type

    data = {'iam': 'TEST001', 'modem': modems[0].id}

    with flask_app.test_client() as client:
        response = client.post(ep, json=data)

    assert response.status_code == 200

    modem = db.session.query(md.RockBlockModem).filter_by(id=modems[0].id).one()
    assert modem.device_type == 'buoy'

    buoy = db.session.query(md.Buoy).filter_by(iam=data['iam']).one()
    assert buoy.rb_id == modem.id


def test_link_handset(create_modems, flask_app, database):
    modems = create_modems
    db = database

    ep = '/v1/handsets/create'

    assert not modems[0].device_type

    data = {'iam': 'HS001', 'modem': modems[0].id}

    with flask_app.test_client() as client:
        response = client.post(ep, json=data)

    assert response.status_code == 200

    modem = db.session.query(md.RockBlockModem).filter_by(id=modems[0].id).one()
    assert modem.device_type == 'handset'

    handset = db.session.query(md.Handset).filter_by(iam=data['iam']).one()
    assert handset.rb_id == modem.id


def test_bad_link(create_modems, flask_app):
    modems = create_modems

    buoy_ep = '/v1/buoys/create'
    handset_ep = '/v1/handsets/create/'

    buoy_data = {'iam': 'PK001', 'modem': modems[0].id}
    handset_data = {'iam': 'HS001', 'modem': modems[1].id}

    with flask_app.test_client() as client:
        r1 = client.post(buoy_ep, json=buoy_data)
        assert r1.status_code == 200
        r2 = client.post(handset_ep, json=handset_data)
        assert r2.status_code == 200

    buoy_cases = [
        ({'iam': buoy_data['iam'], 'modem': modems[2].id},
         [f"Buoy with iam {buoy_data['iam']} already exists", ]),
        ({'iam': 'PK002', 'modem': buoy_data['modem']},
         [f"Modem {buoy_data['modem']} already linked", ]),
        ({'iam': 'PK002', 'modem': handset_data['modem']},
         [f"Modem {handset_data['modem']} already linked", ]),
        ({'iam': '', 'modem': modems[2].id},
         [f"Missing Buoy label", ]),
        ({'iam': 'PK002', 'modem': 999},
         [f"Bad modem ID: 999", ]),
        ({'iam': 'PK002', 'modem': ''},
         [f"Missing Modem", ]),
    ]

    for case in buoy_cases:
        with flask_app.test_client() as client:
            r = client.post(buoy_ep, json=case[0])
        assert r.status_code == 500
        errors = r.json
        assert errors
        for err in case[1]:
            assert err in errors

    handset_cases = [
        ({'iam': handset_data['iam'], 'modem': modems[2].id},
         [f"Handset with iam {handset_data['iam']} already exists", ]),
        ({'iam': 'HS002', 'modem': handset_data['modem']},
         [f"Modem {handset_data['modem']} already linked", ]),
        ({'iam': 'HS002', 'modem': buoy_data['modem']},
         [f"Modem {buoy_data['modem']} already linked", ]),
        ({'iam': '', 'modem': modems[2].id},
         [f"Missing Handset label", ]),
        ({'iam': 'HS002', 'modem': 999},
         [f"Bad modem ID: 999", ]),
        ({'iam': 'HS002', 'modem': ''},
         [f"Missing Modem", ]),
    ]

    for case in handset_cases:
        with flask_app.test_client() as client:
            r = client.post(handset_ep, json=case[0])
        assert r.status_code == 500
        errors = r.json
        assert errors
        for err in case[1]:
            assert err in errors


def test_add_route(create_routes, flask_app):
    routes = create_routes

    assert False
