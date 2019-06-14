from flask import Blueprint

fronted = Blueprint('frontend', __name__, static_folder='../static/frontend', static_url_path='static')
