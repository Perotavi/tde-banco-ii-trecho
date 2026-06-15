from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import text

from app.extensions import db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
def painel_admin():
    if not current_user.tem_perfil("admin"):
        flash("Acesso restrito a administradores.", "danger")
        return redirect(url_for("posts.feed"))

    usuarios = db.session.execute(
        text("""
            SELECT
                u.id,
                u.nome,
                u.username,
                u.email,
                u.status_conta,
                u.data_criacao,
                p.nome AS perfil,
                COUNT(DISTINCT posts.id) AS total_posts,
                COUNT(DISTINCT denuncias.id) AS total_denuncias_feitas
            FROM usuarios u
            INNER JOIN perfis p ON u.perfil_id = p.id
            LEFT JOIN posts ON u.id = posts.usuario_id
            LEFT JOIN denuncias ON u.id = denuncias.denunciante_id
            GROUP BY
                u.id,
                u.nome,
                u.username,
                u.email,
                u.status_conta,
                u.data_criacao,
                p.nome
            ORDER BY u.id ASC
        """)
    ).mappings().all()

    logs_login = db.session.execute(
        text("""
            SELECT
                l.id,
                u.nome,
                u.username,
                l.data_login,
                l.ip_acesso
            FROM logs_login l
            INNER JOIN usuarios u ON l.usuario_id = u.id
            ORDER BY l.data_login DESC
            LIMIT 10
        """)
    ).mappings().all()

    logs_moderacao = db.session.execute(
        text("""
            SELECT
                log_id,
                acao,
                justificativa,
                data_acao,
                moderador_nome,
                moderador_username,
                usuario_alvo_nome,
                usuario_alvo_username
            FROM view_logs_admin
            ORDER BY data_acao DESC
            LIMIT 10
        """)
    ).mappings().all()

    return render_template(
        "admin.html",
        usuarios=usuarios,
        logs_login=logs_login,
        logs_moderacao=logs_moderacao
    )