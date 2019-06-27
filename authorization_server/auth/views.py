from flask import Blueprint, request, render_template, redirect
from authorization_server import utils, oauth_grand_type as oauth_gt
from authorization_server.auth.forms import AuthorisationForm

auth = Blueprint('auth', __name__, static_folder='../static/auth')


@auth.route('/code',  methods=['GET', 'POST'])
@utils.login_required('frontend.login', request_args=True, grand_type='code')
def code():
    '''Show the user the authorisation form with the permissions required by the client or either shows an error to
    the user on the same page or redirect the user back to the client with some error code.
    '''
    auth_code = oauth_gt.AuthorisationCode(request.args)
    valid_request = auth_code.validate_request()

    # Is the request valid both in format and semantics => show authorisation form
    if valid_request:
        form = AuthorisationForm()
        return render_template('auth/code.html', client_app=auth_code, form=form, errors=False)

    # ... Or perhaps there is an error that the user should know as specified by oAuth 2.0? => show error on page
    if auth_code.errors['code'] == 400:
        return render_template('auth/code.html', errors=auth_code.errors), 400

    # ...Otherwise there is an error that only concerns the client only => redirect the error
    if auth_code.errors['code'] == 200:
        errors = auth_code.errors
        url = auth_code.redirect_uri
        url += f"?error={errors['error']}&error_description={errors['error_description']}"
        if 'state' in errors:
            url += f"&state={errors['state']}"
        return redirect(url)
