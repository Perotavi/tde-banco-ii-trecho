from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


# Blueprint da área administrativa.
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
def painel_admin():
    """
    Painel de administração.

    Exibe:
    - usuários cadastrados;
    - perfil;
    - status;
    - suspensão;
    - motivo de punição;
    - logs de login;
    - logs de moderação.
    """

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
                u.suspenso_ate,
                u.motivo_punicao,
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
                u.suspenso_ate,
                u.motivo_punicao,
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


@admin_bp.route("/usuario/<int:usuario_id>/status/<novo_status>", methods=["POST"])
@login_required
def alterar_status_usuario(usuario_id, novo_status):
    """
    Admin altera status de um usuário pela tela de administração.

    Pode:
    - ativar;
    - suspender;
    - banir.
    """

    if not current_user.tem_perfil("admin"):
        flash("Acesso restrito a administradores.", "danger")
        return redirect(url_for("posts.feed"))

    if novo_status not in ["ativo", "suspenso", "banido"]:
        flash("Status inválido.", "danger")
        return redirect(url_for("admin.painel_admin"))

    justificativa = request.form.get("justificativa", "").strip()
    duracao_horas = request.form.get("duracao_horas", "24").strip()

    if not justificativa:
        justificativa = f"Status alterado para {novo_status} pelo administrador."

    try:
        db.session.execute(
            text("""
                CALL sp_alterar_status_usuario(
                    :admin_id,
                    :usuario_alvo_id,
                    :novo_status,
                    :justificativa
                )
            """),
            {
                "admin_id": current_user.id,
                "usuario_alvo_id": usuario_id,
                "novo_status": novo_status,
                "justificativa": justificativa
            }
        )

        if novo_status == "suspenso":
            try:
                duracao_horas_int = int(duracao_horas)
            except ValueError:
                duracao_horas_int = 24

            if duracao_horas_int <= 0:
                duracao_horas_int = 24

            suspenso_ate = datetime.now() + timedelta(hours=duracao_horas_int)

            db.session.execute(
                text("""
                    UPDATE usuarios
                    SET suspenso_ate = :suspenso_ate
                    WHERE id = :usuario_id
                """),
                {
                    "suspenso_ate": suspenso_ate,
                    "usuario_id": usuario_id
                }
            )

        db.session.commit()

        flash(f"Status alterado para {novo_status}.", "success")

    except SQLAlchemyError as erro:
        db.session.rollback()
        flash(f"Erro ao alterar status: {erro}", "danger")

    return redirect(url_for("admin.painel_admin"))


@admin_bp.route("/usuario/<int:usuario_id>/perfil/<novo_perfil>", methods=["POST"])
@login_required
def alterar_perfil_usuario(usuario_id, novo_perfil):
    """
    Admin altera o perfil de um usuário.

    Perfis aceitos:
    - usuario;
    - moderador;
    - analista;
    - admin.
    """

    if not current_user.tem_perfil("admin"):
        flash("Acesso restrito a administradores.", "danger")
        return redirect(url_for("posts.feed"))

    if novo_perfil not in ["usuario", "moderador", "analista", "admin"]:
        flash("Perfil inválido.", "danger")
        return redirect(url_for("admin.painel_admin"))

    justificativa = request.form.get("justificativa", "").strip()

    if not justificativa:
        justificativa = f"Perfil alterado para {novo_perfil} pelo administrador."

    try:
        db.session.execute(
            text("""
                CALL sp_alterar_perfil_usuario(
                    :admin_id,
                    :usuario_alvo_id,
                    :novo_perfil,
                    :justificativa
                )
            """),
            {
                "admin_id": current_user.id,
                "usuario_alvo_id": usuario_id,
                "novo_perfil": novo_perfil,
                "justificativa": justificativa
            }
        )
        db.session.commit()

        flash(f"Perfil alterado para {novo_perfil}.", "success")

    except SQLAlchemyError as erro:
        db.session.rollback()
        flash(f"Erro ao alterar perfil: {erro}", "danger")

    return redirect(url_for("admin.painel_admin"))