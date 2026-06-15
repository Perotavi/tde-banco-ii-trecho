from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import text

from app.extensions import db

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")


@relatorios_bp.route("/")
@login_required
def painel_relatorios():
    if not current_user.tem_perfil("analista", "admin"):
        flash("Acesso restrito a analistas e administradores.", "danger")
        return redirect(url_for("posts.feed"))

    ranking_posts = db.session.execute(
        text("""
            SELECT
                post_id,
                conteudo,
                autor_username,
                total_curtidas,
                total_comentarios,
                total_denuncias
            FROM view_relatorio_engajamento
            ORDER BY
                (total_curtidas + total_comentarios - total_denuncias) DESC,
                post_id DESC
            LIMIT 10
        """)
    ).mappings().all()

    usuarios_por_perfil = db.session.execute(
        text("""
            SELECT
                p.nome AS perfil,
                COUNT(u.id) AS total
            FROM perfis p
            LEFT JOIN usuarios u ON p.id = u.perfil_id
            GROUP BY p.nome
            ORDER BY total DESC
        """)
    ).mappings().all()

    denuncias_por_status = db.session.execute(
        text("""
            SELECT
                status_denuncia,
                COUNT(*) AS total
            FROM denuncias
            GROUP BY status_denuncia
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
        "relatorios.html",
        ranking_posts=ranking_posts,
        usuarios_por_perfil=usuarios_por_perfil,
        denuncias_por_status=denuncias_por_status,
        logs_moderacao=logs_moderacao
    )