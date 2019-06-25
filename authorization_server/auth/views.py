from flask import Blueprint, request, render_template
from authorization_server import oauth_grand_type as oauth_gt

auth = Blueprint('auth', __name__, static_folder='../static/auth')


@auth.route('/code',  methods=['GET'])
def grand_type_code():
    return render_template('auth/code.html'), 400
