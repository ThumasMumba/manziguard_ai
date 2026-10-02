"""
This module initializes the Flask extensions used in the application, including SQLAlchemy for database interactions, 
LoginManager for user session management, and Limiter for rate limiting.
     """


from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_babel import Babel 
from flask_login import LoginManager
from flask_limiter import Limiter

# Instantiated here (not in app.py) so models.py and app.py can both
# import them without creating a circular import.

db = SQLAlchemy() # Database instance for ORM and database interactions
csrf = CSRFProtect() # CSRF protection for forms to prevent cross-site request forgery attacks
login_manager = LoginManager()
babel = Babel()     #Internationalization and localization support for the application
limiter = Limiter(key_func=get_remote_address)  # Global rate limiting for all routes       