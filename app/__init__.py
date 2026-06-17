from flask import Flask

from config import Config
from app.extensions import db, login_manager


def create_app():
    """
    Cria e configura a aplicação Flask.

    Aqui ficam:
    - configuração da aplicação;
    - inicialização do banco;
    - configuração do Flask-Login;
    - registro dos blueprints.
    """

    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializa o SQLAlchemy com a aplicação.
    db.init_app(app)

    # Inicializa o Flask-Login.
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    # Importa os blueprints dentro da função para evitar import circular.
    from app.auth.routes import auth_bp
    from app.posts.routes import posts_bp
    from app.moderacao.routes import moderacao_bp
    from app.relatorios.routes import relatorios_bp
    from app.admin.routes import admin_bp
    from app.perfil.routes import perfil_bp
    from app.notificacoes.routes import notificacoes_bp

    # Registra as rotas principais do sistema.
    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(moderacao_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(perfil_bp)
    app.register_blueprint(notificacoes_bp)

    return app