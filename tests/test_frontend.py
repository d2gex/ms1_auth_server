def test_registration_form(frontend_app):
    '''Test the registration form as follows:

    1) Registration page is served at /
    2) When all required fields are sent and they have the right format => users are redirected to login
    3) If any required field is missing => form should be invalid and error shown
    '''

    # (1)
    response = frontend_app.get('/')
    assert response.status_code == 200
    assert 'Sign Up' in response.get_data(as_text=True)

    # (2)
    data = {'firstname': 'John',
            'lastname': 'Doe',
            'email': 'validemail@example.com',
            'password': 'password',
            'confirm_password': 'password'}
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'login page!' in response.get_data(as_text=True)

    # (3.1)
    original_value = data['firstname']
    data['firstname'] = ''
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'field is required' in response.get_data(as_text=True)

    # (3.2)
    data['firstname'] = original_value
    original_value = data['email']
    data['email'] = 'this is not a valid email'
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Please enter a valid email address' in response.get_data(as_text=True)

    # (3.3)
    data['email'] = original_value
    original_value = data['password']
    data['password'] = '123456'
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Your password must be between 8  and 15 characters long' in response.get_data(as_text=True)

    # (3.3)
    data['password'] = original_value
    original_value = data['confirm_password']
    data['confirm_password'] = '123456'
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Please enter the same password again' in response.get_data(as_text=True)


