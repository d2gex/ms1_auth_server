import functools
import secrets

from os.path import join
from sqlalchemy import Table
from authorization_server import config, models
from authorization_server.app import db, bcrypt

table_names = [models.User, models.AuthorisationCode, models.Application]
TEST_PATH = join(config.ROOT_PATH, 'tests')


def queries(tables):
    '''Generator that will create the required queries to reset a list of tables passed as parameters
    '''
    for obj in tables:
        yield db.session.execute(obj.delete()) if isinstance(obj, Table) else db.session.query(obj).delete()


def reset_database(tear='up', tables=None):
    ''' Reset the database before, after or before and after the method being decorated is executed.
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _tables = table_names if not tables else tables
            if tear in ('up', 'up_down'):
                list(queries(_tables))
                db.session.commit()
            ret = func(*args, **kwargs)
            if tear in ('down', 'up_down'):
                list(queries(_tables))
                db.session.commit()
            return ret
        return wrapper
    return decorator


def generate_pair_client_model_data(constraints):
    '''Generates a pair of client-data-like rows ready to be inserted in the local database, according to the given
    constraints

    '''
    rows = []
    for _ in range(2):
        domain = f"https://{secrets.token_hex(12)}.appdomain.com"
        rows.append({
            'id': secrets.token_hex(9),
            'reg_token': secrets.token_hex(10),
            'email': f"{secrets.token_hex(11)}@appdomain.com",
            'web_url': domain,
            'redirect_uri': f"{domain}/callback",
            'name': 'App Name',
            'description': 'App Description...',
            'client_secret': 'abcD1234'
        })

    if all(value for key, value in constraints.items()):
        return rows

    if not constraints['id']:
        rows[0]['id'] = rows[-1]['id'] = 'same_id'

    if not constraints['reg_token']:
        rows[0]['reg_token'] = rows[-1]['reg_token'] = 'same_token'

    if not constraints['email']:
        rows[0]['email'] = rows[-1]['email'] = 'same.email@appdomain.com'

    if not constraints['web_url']:
        rows[0]['web_url'] = rows[-1]['web_url'] = 'https://appdomain.com'

    if not constraints['redirect_uri']:
        rows[0]['redirect_uri'] = rows[-1]['redirect_uri'] = 'https://appdomain.com/callback'

    if not constraints['name']:
        rows[0]['name'] = rows[-1]['name'] = None

    if not constraints['description']:
        rows[0]['description'] = rows[-1]['description'] = None

    return rows


def generate_model_user_instance(random=False):
    if random:
        return {
            'firstname': secrets.token_hex(10),
            'lastname': secrets.token_hex(10),
            'email': f"{secrets.token_hex(10)}@example.com",
            'password': secrets.token_hex(10)
        }
    return {
        'firstname': 'First Name',
        'lastname': 'Last Name',
        'email': "firstname.lastname@example.com",
        'password': 'abcD1234'
    }


def add_user_client_context_to_db():
    '''Add user and client data to the database to emulate a real case scenario
    '''
    constraints = {
        'id': True,
        'email': True,
        'reg_token': True,
        'web_url': True,
        'redirect_uri': True,
        'name': True,
        'description': True
    }
    client_data = generate_pair_client_model_data(constraints)
    client = models.Application(**client_data[0])
    client.client_secret = bcrypt.generate_password_hash(client_data[0]['client_secret']).decode()
    client.is_allowed = True
    user_data = generate_model_user_instance()
    user = models.User(**user_data)
    user.password = bcrypt.generate_password_hash(user_data['password']).decode()
    db.session.add(client)
    db.session.add(user)
    db.session.commit()

    client_data[0]['id'] = client.id
    user_data['id'] = user.id
    return client_data, user_data


def perform_logged_in(app_instance, user_data):
    data = {
        'email': user_data['email'],
        'password': user_data['password']
    }
    response = app_instance.post('/login', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Account Details' in response.get_data(as_text=True)
    with app_instance.session_transaction() as session:
        assert 'user_id' in session
