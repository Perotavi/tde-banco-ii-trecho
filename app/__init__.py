from flask import Flask
from config import Config
from app.extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from app.auth.routes import auth_bp
    from app.posts.routes import posts_bp
    from app.moderacao.routes import moderacao_bp
    from app.relatorios.routes import relatorios_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(moderacao_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(admin_bp)

    return app