from flask import Blueprint, request, render_template
from authorization_server import oauth_grand_type as oauth_gt
from authorization_server.auth.forms import AuthorisationForm

auth = Blueprint('auth', __name__, static_folder='../static/auth')


@auth.route('/code',  methods=['GET'])
def index():
    client_app = {
        'name': 'Application Name',
        'web_url': 'https://www.applicationdomain.com'
    }
    form = AuthorisationForm()
    return render_template('auth/code.html', client_app=client_app, form=form)
