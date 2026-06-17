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

    bio = db.Column(db.String(280))
    foto_perfil_url = db.Column(db.String(500))
    capa_perfil_url = db.Column(db.String(500))

    data_criacao = db.Column(db.DateTime)

    perfil = db.relationship("Perfil", back_populates="usuarios")
    posts = db.relationship("Post", back_populates="usuario")

    comentarios = db.relationship("Comentario", back_populates="usuario")
    curtidas = db.relationship("Curtida", back_populates="usuario")

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def tem_perfil(self, *perfis_permitidos):
        if not self.perfil:
            return False

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
    comentarios = db.relationship("Comentario", back_populates="post")
    curtidas = db.relationship("Curtida", back_populates="post")


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

    post = db.relationship("Post", back_populates="comentarios")
    usuario = db.relationship("Usuario", back_populates="comentarios")


class Curtida(db.Model):
    __tablename__ = "curtidas"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data_curtida = db.Column(db.DateTime)

    post = db.relationship("Post", back_populates="curtidas")
    usuario = db.relationship("Usuario", back_populates="curtidas")


class Seguidor(db.Model):
    __tablename__ = "seguidores"

    id = db.Column(db.Integer, primary_key=True)
    seguidor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    seguido_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data_seguindo = db.Column(db.DateTime)

    seguidor = db.relationship(
        "Usuario",
        foreign_keys=[seguidor_id],
        backref="seguindo"
    )

    seguido = db.relationship(
        "Usuario",
        foreign_keys=[seguido_id],
        backref="seguidores"
    )


class Bloqueio(db.Model):
    __tablename__ = "bloqueios"

    id = db.Column(db.Integer, primary_key=True)
    bloqueador_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    bloqueado_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data_bloqueio = db.Column(db.DateTime)

    bloqueador = db.relationship(
        "Usuario",
        foreign_keys=[bloqueador_id],
        backref="bloqueios_realizados"
    )

    bloqueado = db.relationship(
        "Usuario",
        foreign_keys=[bloqueado_id],
        backref="bloqueios_recebidos"
    )


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

    post = db.relationship("Post", backref="denuncias")
    denunciante = db.relationship("Usuario", backref="denuncias_feitas")


class Notificacao(db.Model):
    __tablename__ = "notificacoes"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    origem_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))
    comentario_id = db.Column(db.Integer, db.ForeignKey("comentarios.id"))

    tipo = db.Column(db.String(50), nullable=False)
    mensagem = db.Column(db.String(255), nullable=False)
    lida = db.Column(db.Boolean, nullable=False, default=False)
    data_criacao = db.Column(db.DateTime)

    usuario = db.relationship(
        "Usuario",
        foreign_keys=[usuario_id],
        backref="notificacoes"
    )

    origem_usuario = db.relationship(
        "Usuario",
        foreign_keys=[origem_usuario_id],
        backref="notificacoes_geradas"
    )

    post = db.relationship("Post", backref="notificacoes")
    comentario = db.relationship("Comentario", backref="notificacoes")


class LogModeracao(db.Model):
    __tablename__ = "logs_moderacao"

    id = db.Column(db.Integer, primary_key=True)
    moderador_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))
    usuario_alvo_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    acao = db.Column(db.String(100), nullable=False)
    justificativa = db.Column(db.String(255), nullable=False)
    data_acao = db.Column(db.DateTime)

    moderador = db.relationship(
        "Usuario",
        foreign_keys=[moderador_id],
        backref="logs_moderacao_realizados"
    )

    usuario_alvo = db.relationship(
        "Usuario",
        foreign_keys=[usuario_alvo_id],
        backref="logs_moderacao_recebidos"
    )

    post = db.relationship("Post", backref="logs_moderacao")


class LogLogin(db.Model):
    __tablename__ = "logs_login"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    data_login = db.Column(db.DateTime)
    ip_acesso = db.Column(db.String(45))

    usuario = db.relationship("Usuario", backref="logs_login")


@login_manager.user_loader
def load_user(usuario_id):
    return Usuario.query.get(int(usuario_id))
