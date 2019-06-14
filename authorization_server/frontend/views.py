from flask import Blueprint, render_template

fronted = Blueprint('frontend', __name__, static_folder='../static/frontend')


@fronted.route('/')
def index():
    return render_template('frontend/register.html')