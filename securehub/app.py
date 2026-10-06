import os
from flask import Flask, render_template
from flask_login import LoginManager
from config import Config
from models import db
from models.user import User

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance directory exists
    instance_path = os.path.join(app.root_path, 'instance')
    os.makedirs(instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access SECUREHUB portal.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.profile import profile_bp
    from routes.users import users_bp
    from routes.departments import departments_bp
    from routes.orders import orders_bp
    from routes.documents import documents_bp
    from routes.tickets import tickets_bp
    from routes.reports import reports_bp
    from routes.notifications import notifications_bp
    from routes.settings import settings_bp
    from routes.admin import admin_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Register Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Auto-initialize & Seed Database
    with app.app_context():
        from utils.seed import seed_database
        seed_database()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002, debug=True)
