from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import text

from app.extensions import db


# Blueprint da tela de notificações.
notificacoes_bp = Blueprint("notificacoes", __name__, url_prefix="/notificacoes")


@notificacoes_bp.route("/")
@login_required
def listar_notificacoes():
    """
    Lista as notificações do usuário logado.

    As notificações são geradas por:
    - curtidas;
    - comentários;
    - futuramente outras ações.
    """

    notificacoes = db.session.execute(
        text("""
            SELECT
                n.id,
                n.tipo,
                n.mensagem,
                n.lida,
                n.data_criacao,
                n.post_id,

                origem.nome AS origem_nome,
                origem.username AS origem_username

            FROM notificacoes n

            LEFT JOIN usuarios origem ON n.origem_usuario_id = origem.id

            WHERE n.usuario_id = :usuario_id

            ORDER BY n.data_criacao DESC
        """),
        {"usuario_id": current_user.id}
    ).mappings().all()

    return render_template(
        "notificacoes.html",
        notificacoes=notificacoes
    )


@notificacoes_bp.route("/marcar-lidas", methods=["POST"])
@login_required
def marcar_como_lidas():
    """
    Marca todas as notificações do usuário logado como lidas.
    """

    db.session.execute(
        text("""
            UPDATE notificacoes
            SET lida = TRUE
            WHERE usuario_id = :usuario_id
        """),
        {"usuario_id": current_user.id}
    )
    db.session.commit()

    flash("Notificações marcadas como lidas.", "success")

    return redirect(url_for("notificacoes.listar_notificacoes"))