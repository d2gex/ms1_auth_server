from flask_login import current_user
from sqlalchemy import Table
from unittest.mock import patch
from tests import utils as test_utils
from authorization_server import models
from authorization_server.app import db


def test_queries():
    '''Test queries generator generates the right delete queries depending on the type of object of a given list
    '''

    tables = [Table(), Table(), models.User(), models.User(), models.User()]
    with patch.object(test_utils.db.session, 'execute') as ex_table:
        with patch.object(test_utils.db.session, 'query') as qy_model:
            list(test_utils.queries(tables))
    assert ex_table.call_count == 2
    assert qy_model.call_count == 3


def test_reset_database():
    '''Test that reset_database works as follows:

    1) When tear='up' => the generator is only consumed once and before foo executes.
    2) When tear='down' => the generator is only consumed once and after bar executes.
    2) When tear='up_down' => the generator is consumed twice, before and after foo_bar.

    '''

    tables = [Table(), Table(), models.User(), models.User(), models.User()]
    with patch.object(test_utils.db.session, 'execute') as ex_table:
        with patch.object(test_utils.db.session, 'query') as qy_model:
            with patch.object(test_utils.db.session, 'commit'):

                # (1)
                @test_utils.reset_database(tear='up', tables=tables)
                def foo():
                    # By the time this lines run, the database should have been reset so ex_table and qy_model should
                    # have already a value
                    assert ex_table.call_count == 2
                    assert qy_model.call_count == 3

                foo()
                assert ex_table.call_count == 2
                assert qy_model.call_count == 3

                ex_table.reset_mock()
                qy_model.reset_mock()

                # (2)
                @test_utils.reset_database(tear='down', tables=tables)
                def bar():
                    # By the time this lines run, the database should have been reset so ex_table and qy_model should
                    # have already a value
                    assert ex_table.call_count == 0
                    assert qy_model.call_count == 0

                bar()
                assert ex_table.call_count == 2
                assert qy_model.call_count == 3

                ex_table.reset_mock()
                qy_model.reset_mock()

                # (3)
                @test_utils.reset_database(tear='up_down', tables=tables)
                def foo_bar():
                    # By the time this lines run, the database should have been reset so ex_table and qy_model should
                    # have already a value
                    assert ex_table.call_count == 2
                    assert qy_model.call_count == 3

                foo_bar()
                assert ex_table.call_count == 4
                assert qy_model.call_count == 6


def test_generate_pair_client_model_data():
    '''Ensure that the following occurs:

    1) If not constraints => the two generated rows have all their field unique
    2) if id constraint is not present => id is the same
    3) if reg_token constraint is not present => reg_token is the same
    4) if email constraint is not present => email is the same
    5) if web_url constraint is not present => web_url is the same
    6) if redirect_url constraint is not present => web_url is the same
    7) if name constraint is not present => name is None
    8) if description constraint is not present => description is None
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

    # (1)
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['id'] != rows[1]['id']
    assert rows[0]['email'] != rows[1]['email']
    assert rows[0]['reg_token'] != rows[1]['reg_token']
    assert rows[0]['web_url'] != rows[1]['web_url']
    assert rows[0]['redirect_uri'] != rows[1]['redirect_uri']

    # (2)
    constraints['id'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['id'] == rows[-1]['id']
    assert rows[0]['client_secret'] == rows[1]['client_secret']

    # (3)
    constraints['reg_token'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['reg_token'] == rows[-1]['reg_token']
    assert rows[0]['client_secret'] == rows[1]['client_secret']

    # (4)
    constraints['email'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['email'] == rows[-1]['email']
    assert rows[0]['client_secret'] == rows[1]['client_secret']

    # (5)
    constraints['web_url'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['web_url'] == rows[-1]['web_url']
    assert rows[0]['client_secret'] == rows[1]['client_secret']

    # (6)
    constraints['redirect_uri'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['redirect_uri'] == rows[-1]['redirect_uri']
    assert rows[0]['client_secret'] == rows[1]['client_secret']

    # (7)
    constraints['description'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert not any([rows[0]['description'], rows[-1]['description']])
    assert rows[0]['client_secret'] == rows[1]['client_secret']


def test_generate_model_user_instance():
    '''Test that when generating a sample user, either random or not has all the required fields
    '''

    # (1.1) Ensure the expected keywords are produced
    assert all([keyword in test_utils.generate_model_user_instance(random=True).items()]
               for keyword in ['firstname', 'lastname', 'email', 'password'])

    # (1.2) Ensure values produced are unique
    unique_values = set()
    num_attempts = 50
    for _ in range(num_attempts):
        unique_values.update({value for key, value in test_utils.generate_model_user_instance(random=True).items()})
    assert num_attempts * 4 == len(unique_values)

    # (1.3) Ensure 1/4 of the values are of email-type.
    assert len([x for x in unique_values if '@' in x]) == num_attempts

    # (2.1) Ensure the expected keywords are produced
    assert all([keyword in test_utils.generate_model_user_instance().items()]
               for keyword in ['firstname', 'lastname', 'email', 'password'])


def test_add_user_client_context_to_db():

    assert not db.session.query(models.Application).all()
    assert not db.session.query(models.User).all()
    test_utils. add_user_client_context_to_db()
    assert db.session.query(models.Application).one()
    assert db.session.query(models.User).one()


def test_perform_logged_in(frontend_app):

    client_data, user_data = test_utils.add_user_client_context_to_db()

    # (1)
    response = frontend_app.get('/login')
    assert response.status_code == 200
    assert all([keyword in response.get_data(as_text=True)]
               for keyword in ['Forgot Password?', 'This application would like:'])
    with frontend_app.session_transaction() as b_session:
        assert 'user_id' not in b_session

    # (2)
    test_utils.perform_logged_in(frontend_app, user_data)
    frontend_app.get('/login')
    with frontend_app.session_transaction() as b_session:
        assert 'user_id' in b_session
