from sqlalchemy import Table
from unittest.mock import patch
from tests import utils as test_utils
from authorization_server import models


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

    # (3)
    constraints['reg_token'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['reg_token'] == rows[-1]['reg_token']

    # (4)
    constraints['email'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['email'] == rows[-1]['email']

    # (5)
    constraints['web_url'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['web_url'] == rows[-1]['web_url']

    # (6)
    constraints['redirect_uri'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert rows[0]['redirect_uri'] == rows[-1]['redirect_uri']

    # (7)
    constraints['description'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    assert not any([rows[0]['description'], rows[-1]['description']])
