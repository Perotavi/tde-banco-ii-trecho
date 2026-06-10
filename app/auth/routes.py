from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from sqlalchemy import text

from app.extensions import db
from app.models import Usuario

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


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

        if usuario.status_conta != "ativo":
            flash("Esta conta não está ativa.", "warning")
            return redirect(url_for("auth.login"))

        login_user(usuario)

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

        flash(f"Bem-vindo(a), {usuario.nome}!", "success")
        return redirect(url_for("posts.feed"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))