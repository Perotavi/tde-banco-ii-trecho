from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from sqlalchemy import text

from app.extensions import db
from app.models import Usuario

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def registrar_log_login(usuario):
    db.session.execute(
        text("""
            INSERT INTO logs_login (usuario_id, ip_acesso)
            VALUES (:usuario_id, :ip_acesso)
        """),
        {
            "usuario_id": usuario.id,
            "ip_acesso": request.remote_addr
        }
    )
    db.session.commit()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("posts.feed"))

    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario or not usuario.verificar_senha(senha):
            flash("E-mail ou senha inválidos.", "danger")
            return redirect(url_for("auth.login"))

        if usuario.status_conta == "banido":
            session["aviso_banido"] = True
            return redirect(url_for("auth.login"))

        if usuario.status_conta == "suspenso":
            if usuario.suspenso_ate and usuario.suspenso_ate <= datetime.now():
                usuario.status_conta = "ativo"
                usuario.suspenso_ate = None
                usuario.motivo_punicao = None
                db.session.commit()

                login_user(usuario)
                registrar_log_login(usuario)

                flash(f"Bem-vindo(a), {usuario.nome}!", "success")
                return redirect(url_for("posts.feed"))

            login_user(usuario)
            registrar_log_login(usuario)

            if usuario.suspenso_ate:
                session["suspenso_ate_texto"] = usuario.suspenso_ate.strftime("%d/%m/%Y às %H:%M")
            else:
                session["suspenso_ate_texto"] = "prazo não definido"

            session["aviso_suspenso"] = True
            return redirect(url_for("posts.feed"))

        login_user(usuario)
        registrar_log_login(usuario)

        flash(f"Bem-vindo(a), {usuario.nome}!", "success")
        return redirect(url_for("posts.feed"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))