import json
import uuid

from authorization_server import models
from authorization_server.app import db

RESOURCE_URI = '/api/client/registration'


def test_post(frontend_app):
    '''Test than we posting to /registration:

    1) If data provided isn't the expected data structure => throw 400
    2) if data provided misses any expected key => 400
    3) if the redirect_uri isn't a valid url => 409
    5) if the client's email is already register => 409
    6) Otherwise create client record and return client_id
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
        'description': 'App Domain ...',
        'web_url': 'https://www.appdomain.com',
        'redirect_uri': 'https://this is not a valid url'
    }

    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 409
    ret_data = response.get_json()
    assert 409 == ret_data['error']['code']
    assert all(keyword in ret_data['error']['message'] for keyword in ('while processing', 'A valid url must start by'))

    # (4)
    post_data['redirect_uri'] = 'https://appdomain.com/callback?landing_page=xxxx'
    post_data['web_url'] = 'This is not a valid url'

    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 409
    ret_data = response.get_json()
    assert 409 == ret_data['error']['code']
    assert all(keyword in ret_data['error']['message'] for keyword in ('while processing', 'A valid url must start by'))

    # (5)
    post_data['web_url'] = 'https://www.appdomain.com'
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

    # (6)
    db.session.query(models.Application).delete()
    db.session.commit()
    assert not db.session.query(models.Application).all()
    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 201
    ret_data = response.get_json()
    assert ret_data['id']
    assert db.session.query(models.Application).filter_by(email=post_data['email']).first()
