from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


# Blueprint do painel de moderação.
moderacao_bp = Blueprint("moderacao", __name__, url_prefix="/moderacao")


@moderacao_bp.route("/")
@login_required
def painel_moderacao():
    """
    Exibe o painel de moderação.

    Apenas moderadores e administradores podem acessar.
    """

    if not current_user.tem_perfil("moderador", "admin"):
        flash("Acesso restrito a moderadores e administradores.", "danger")
        return redirect(url_for("posts.feed"))

    denuncias = db.session.execute(
        text("""
            SELECT
                denuncia_id,
                motivo,
                status_denuncia,
                data_denuncia,

                post_id,
                conteudo_denunciado,
                status_post,

                autor_id,
                autor_nome,
                autor_username,
                autor_perfil,

                denunciante_id,
                denunciante_nome,
                denunciante_username

            FROM view_denuncias_moderacao

            WHERE status_denuncia = 'pendente'

            ORDER BY data_denuncia ASC
        """)
    ).mappings().all()

    return render_template("moderacao.html", denuncias=denuncias)


@moderacao_bp.route("/post/<int:post_id>/<acao>", methods=["POST"])
@login_required
def moderar_post(post_id, acao):
    """
    Oculta ou remove um post denunciado.

    Usa a procedure sp_moderar_post para validar regras no banco.
    """

    if not current_user.tem_perfil("moderador", "admin"):
        flash("Apenas moderadores e administradores podem moderar posts.", "danger")
        return redirect(url_for("posts.feed"))

    if acao not in ["ocultar", "remover"]:
        flash("Ação inválida.", "danger")
        return redirect(url_for("moderacao.painel_moderacao"))

    justificativa = request.form.get("justificativa", "").strip()

    if not justificativa:
        justificativa = f"Post marcado como {acao} pela moderação."

    try:
        db.session.execute(
            text("""
                CALL sp_moderar_post(
                    :moderador_id,
                    :post_id,
                    :acao,
                    :justificativa
                )
            """),
            {
                "moderador_id": current_user.id,
                "post_id": post_id,
                "acao": acao,
                "justificativa": justificativa
            }
        )
        db.session.commit()

        flash("Ação de moderação realizada com sucesso.", "success")

    except SQLAlchemyError as erro:
        db.session.rollback()
        flash(f"Erro ao moderar post: {erro}", "danger")

    return redirect(url_for("moderacao.painel_moderacao"))


@moderacao_bp.route("/usuario/<int:usuario_id>/<novo_status>", methods=["POST"])
@login_required
def alterar_status_usuario(usuario_id, novo_status):
    """
    Suspende, bane ou reativa um usuário pelo painel de moderação.

    O campo duracao_horas é usado quando o status for suspenso.
    """

    if not current_user.tem_perfil("moderador", "admin"):
        flash("Apenas moderadores e administradores podem alterar status de usuários.", "danger")
        return redirect(url_for("posts.feed"))

    if novo_status not in ["ativo", "suspenso", "banido"]:
        flash("Status inválido.", "danger")
        return redirect(url_for("moderacao.painel_moderacao"))

    justificativa = request.form.get("justificativa", "").strip()
    duracao_horas = request.form.get("duracao_horas", "24").strip()

    if not justificativa:
        justificativa = f"Usuário marcado como {novo_status} pela moderação."

    try:
        db.session.execute(
            text("""
                CALL sp_alterar_status_usuario(
                    :moderador_id,
                    :usuario_alvo_id,
                    :novo_status,
                    :justificativa
                )
            """),
            {
                "moderador_id": current_user.id,
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

        flash(f"Status do usuário alterado para {novo_status}.", "success")

    except SQLAlchemyError as erro:
        db.session.rollback()
        flash(f"Erro ao alterar status do usuário: {erro}", "danger")

    return redirect(url_for("moderacao.painel_moderacao"))