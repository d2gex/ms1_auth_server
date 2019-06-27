import functools
import secrets

from os.path import join
from sqlalchemy import Table
from authorization_server import config, models
from authorization_server.app import db

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
