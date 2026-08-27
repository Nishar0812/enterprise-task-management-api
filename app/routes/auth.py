# Registration, login, and token refresh endpoints are implemented in the
# authentication milestone. The blueprint is wired up now so the app factory
# and URL prefix structure do not need to change later.
from flask import Blueprint

auth_bp = Blueprint("auth", __name__)
