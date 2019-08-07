from flask import Blueprint, request, render_template, redirect, session, url_for
from authorization_server import utils, oauth_grand_type as oauth_gt
from authorization_server.auth.forms import AuthorisationForm

auth = Blueprint('auth', __name__, static_folder='../static/auth')


@auth.route('/code_request',  methods=['GET', 'POST'])
@utils.login_required('frontend.login', request_args=True, grand_type='code')
def code_request():
    '''Handle the authorisation request from a client application.
    '''
    auth_code = oauth_gt.AuthorisationCode(request.args)
    valid_request = auth_code.validate_request()

    # Is the request valid both in format and semantics => show authorisation form
    if valid_request:
        form = AuthorisationForm()
        session['auth_code'] = auth_code.as_dict()
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


@auth.route('/code_response',  methods=['GET', 'POST'])
@utils.login_required('frontend.login', request_args=True, grand_type='code')
def code_response():
    ''' Handle the authorisation response to be sent to a client after user's decision.
    '''

    # Not coming from code_request? => redirect to code_request
    if 'auth_code' not in session:
        return redirect(url_for('auth.code_request'))

    # Coming from code_request but form was not submitted => redirect back to code_request
    form = AuthorisationForm()
    if not form.validate_on_submit():
        return redirect(url_for('auth.code_request'))

    # Process response from Resource Owner
    auth_code_request = session['auth_code']
    url = auth_code_request['redirect_uri']
    if form.cancel.data:
        error_description = "The resource owner explicitly denied the required sought permissions"
        url += f"?error={oauth_gt.CLIENT_ACCESS_DENIED_ERROR}&" \
               f"error_description={error_description}&" \
               f"state={auth_code_request['state']}"
    elif form.allow.data:
        auth_code = oauth_gt.AuthorisationCode(auth_code_request)
        response = auth_code.response(auth_code_request['client_id'])
        url += f"?code={response['code']}&state={response['state']}"

    return redirect(url)
