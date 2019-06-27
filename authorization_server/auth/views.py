from flask import Blueprint, request, render_template
from authorization_server import utils, oauth_grand_type as oauth_gt
from authorization_server.auth.forms import AuthorisationForm

auth = Blueprint('auth', __name__, static_folder='../static/auth')


@auth.route('/code',  methods=['GET', 'POST'])
@utils.login_required('frontend.login', request_args=True, grand_type='code')
def code():

    # RE-DO: Code just to test the login-required aspect of this view
    auth_code = oauth_gt.AuthorisationCode(**request.args)
    auth_code.validate_request()
    if auth_code.errors['code'] == 400:
        return render_template('auth/code.html', errors=auth_code.errors), 400
