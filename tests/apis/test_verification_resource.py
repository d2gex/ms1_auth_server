import json
import secrets

from authorization_server import models
from authorization_server.app import db, bcrypt
from tests import utils as test_utils

RESOURCE_URI = '/api/auth/verification/'


@test_utils.reset_database()
def test_post(frontend_app):
    '''Test than we posting to /verification:

    1) If data provided isn't the expected data structure => throw 400
    2) if data provided misses any expected key => 400
    3) if a client that does not exist tries to verify => throw 409
    4) If a client exists but isn't yet allowed to verify => throw 409
    5) if a client exists but tokens is different to that in the database => 409
    6) if a client exists but no token is stored in the db  => throw 409
    7) Otherwise the client is verified => response 201
    '''

    # (1)
    response = frontend_app.post(RESOURCE_URI, data=json.dumps([]), content_type='application/json')
    assert response.status_code == 400
    ret_data = response.get_json()
    assert 400 == ret_data['error']['code']
    assert all(keyword in ret_data['error']['message'] for keyword in ('Invalid receive', 'Incorrect type'))

    # (2)
    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps({'key_out_of_scope': 'something'}),
                                 content_type='application/json')
    assert response.status_code == 400
    ret_data = response.get_json()
    assert 400 == ret_data['error']['code']
    assert all(keyword in ret_data['error']['message'] for keyword in ('Invalid receive', 'Required key'))

    # (3)
    client_id = models.Application.generate_id()
    post_data = {
        'id': client_id,
        'reg_token': 'this is a token'
    }
    assert not db.session.query(models.Application).filter_by(email=post_data['id']).all()
    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 409
    ret_data = response.get_json()
    assert all(keyword in ret_data['error']['message'] for keyword in
               ('while processing', client_id, RESOURCE_URI.replace('verification', 'registration')))

    # (4)
    # ---> pre-insert a client with is_allowed flag set to False
    data = dict(post_data)
    data['email'] = 'info@appdomain.com'
    data['name'] = 'App Name'
    data['description'] = 'App Description'
    data['web_url'] = f"https://{secrets.token_hex(14)}domain.com"
    data['redirect_uri'] = f"{data['web_url']}/callback"
    client_app = models.Application(**data)
    db.session.add(client_app)
    db.session.commit()
    assert db.session.query(models.Application).filter_by(email=data['email']).one()

    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 409
    ret_data = response.get_json()
    assert all(keyword in ret_data['error']['message'] for keyword in
               ('while processing', client_id, RESOURCE_URI.replace('verification', 'registration')))

    # (5)
    # --> modify the db to change the value of the stored token and set is_allowed to True
    client_app.reg_token = 'This is another token'
    client_app.is_allowed = True
    db.session.add(client_app)
    db.session.commit()
    db_data = db.session.query(models.Application).filter_by(email=data['email']).one()
    assert db_data.reg_token == client_app.reg_token and db_data.is_allowed == client_app.is_allowed

    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 409
    ret_data = response.get_json()
    assert all(keyword in ret_data['error']['message'] for keyword in
               ('while processing', client_id, RESOURCE_URI.replace('verification', 'registration')))

    # (6)
    # --> modify the db to make the stored token NULL
    client_app.reg_token = None
    db.session.add(client_app)
    db.session.commit()
    db_data = db.session.query(models.Application).filter_by(email=data['email']).one()
    assert db_data.reg_token is None and db_data.is_allowed == client_app.is_allowed

    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 409
    ret_data = response.get_json()
    assert all(keyword in ret_data['error']['message'] for keyword in
               ('while processing', client_id, RESOURCE_URI.replace('verification', 'registration')))

    # (7)
    # --> modify the db to match the store token's value to that pass in the POST
    client_app.reg_token = post_data['reg_token']
    db.session.add(client_app)
    db.session.commit()
    db_data = db.session.query(models.Application).filter_by(email=data['email']).one()
    assert db_data.reg_token == client_app.reg_token and db_data.is_allowed == client_app.is_allowed
    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 201
    # --> id and password should be that stored in the db
    ret_data = response.get_json()
    assert ret_data['id'] == client_id
    db_data = db.session.query(models.Application).filter_by(email=data['email']).one()
    assert bcrypt.check_password_hash(db_data.client_secret, ret_data['client_secret'])
