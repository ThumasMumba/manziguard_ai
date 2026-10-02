from flask import Flask
from app.blueprints.auth import auth_bp
from app.models import User
from app.extension import db, login_manager, limiter, csrf, babel
from app.services.analysis import init_analysis, analysis_bp


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "manziguard_secret_key"
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://root:@localhost/manziguard_ai_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["ALLOW_PLACEHOLDER_CHART"] = True
    # Initialize extensions/ Connects extensions to the Flask app instance
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    csrf.exempt(analysis_bp)
    babel.init_app(app)
    
    # Register blueprints
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

   
    app.register_blueprint(auth_bp)
    app.register_blueprint(analysis_bp)
    init_analysis(app)  # Initialize analysis service with the app
    
    with app.app_context():
        db.create_all()

    return app