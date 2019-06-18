import json
import uuid

from authorization_server import config, models
from authorization_server.app import db, create_app
from tests import utils as test_utils

RESOURCE_URI = '/api/auth/registration/'


@test_utils.reset_database()
def test_post(frontend_app):
    '''Test than we posting to /registration:

    1) If data provided isn't the expected data structure => throw 400
    2) if data provided misses any expected key => 400
    3) if the client's email is already register => 409
    3) Otherwise create client record and return client_id
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
    post_data = {
        'id': str(uuid.uuid4()).replace('-', ''),
        'email': 'info@appdomain.com',
        'name': 'App Domain',
        'description': 'App Domain ...'
    }
    db.session.add(models.Application(**post_data))
    db.session.commit()
    assert db.session.query(models.Application).filter_by(email=post_data['email']).first()
    del post_data['id']
    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 409
    ret_data = response.get_json()
    assert 409 == ret_data['error']['code']
    assert all(keyword in ret_data['error']['message'] for keyword in ('while processing', 'has already been registered'))

    # (4)
    db.session.query(models.Application).delete()
    db.session.commit()
    assert not db.session.query(models.Application).all()
    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 201
    ret_data = response.get_json()
    assert ret_data['client_id']
    assert db.session.query(models.Application).filter_by(email=post_data['email']).first()
