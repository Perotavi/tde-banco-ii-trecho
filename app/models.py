from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


class Perfil(db.Model):
    __tablename__ = "perfis"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    descricao = db.Column(db.String(255), nullable=False)

    usuarios = db.relationship("Usuario", back_populates="perfil")


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil_id = db.Column(db.Integer, db.ForeignKey("perfis.id"), nullable=False)
    status_conta = db.Column(
        db.Enum("ativo", "suspenso", "banido"),
        nullable=False,
        default="ativo"
    )

    suspenso_ate = db.Column(db.DateTime)
    motivo_punicao = db.Column(db.String(255))
    data_criacao = db.Column(db.DateTime)

    perfil = db.relationship("Perfil", back_populates="usuarios")
    posts = db.relationship("Post", back_populates="usuario")

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def tem_perfil(self, *perfis_permitidos):
        return self.perfil.nome in perfis_permitidos


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    conteudo = db.Column(db.String(280), nullable=False)
    status_post = db.Column(
        db.Enum("ativo", "oculto", "removido"),
        nullable=False,
        default="ativo"
    )
    data_publicacao = db.Column(db.DateTime)
    data_atualizacao = db.Column(db.DateTime)

    usuario = db.relationship("Usuario", back_populates="posts")


class Comentario(db.Model):
    __tablename__ = "comentarios"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    conteudo = db.Column(db.String(280), nullable=False)
    status_comentario = db.Column(
        db.Enum("ativo", "removido"),
        nullable=False,
        default="ativo"
    )
    data_comentario = db.Column(db.DateTime)


class Curtida(db.Model):
    __tablename__ = "curtidas"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data_curtida = db.Column(db.DateTime)


class Seguidor(db.Model):
    __tablename__ = "seguidores"

    id = db.Column(db.Integer, primary_key=True)
    seguidor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    seguido_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data_seguindo = db.Column(db.DateTime)


class Denuncia(db.Model):
    __tablename__ = "denuncias"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    denunciante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    status_denuncia = db.Column(
        db.Enum("pendente", "analisada", "rejeitada"),
        nullable=False,
        default="pendente"
    )
    data_denuncia = db.Column(db.DateTime)


class LogModeracao(db.Model):
    __tablename__ = "logs_moderacao"

    id = db.Column(db.Integer, primary_key=True)
    moderador_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))
    usuario_alvo_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    acao = db.Column(db.String(100), nullable=False)
    justificativa = db.Column(db.String(255), nullable=False)
    data_acao = db.Column(db.DateTime)


class LogLogin(db.Model):
    __tablename__ = "logs_login"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data_login = db.Column(db.DateTime)
    ip_acesso = db.Column(db.String(45))


@login_manager.user_loader
def load_user(usuario_id):
    return Usuario.query.get(int(usuario_id))