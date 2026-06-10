from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Post

posts_bp = Blueprint("posts", __name__)


@posts_bp.route("/")
def feed():
    posts = (
        Post.query
        .filter_by(status_post="ativo")
        .order_by(Post.data_publicacao.desc())
        .all()
    )

    return render_template("feed.html", posts=posts)

@posts_bp.route("/criar-post-feed", methods=["POST"])
@login_required
def criar_post_feed():
    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para criar posts.", "danger")
        return redirect(url_for("posts.feed"))

    conteudo = request.form.get("conteudo", "").strip()

    if not conteudo:
        flash("O conteúdo do post não pode estar vazio.", "warning")
        return redirect(url_for("posts.feed"))

    if len(conteudo) > 280:
        flash("O post deve ter no máximo 280 caracteres.", "warning")
        return redirect(url_for("posts.feed"))

    try:
        db.session.execute(
            text("CALL sp_criar_post(:usuario_id, :conteudo)"),
            {
                "usuario_id": current_user.id,
                "conteudo": conteudo
            }
        )
        db.session.commit()

        flash("Post publicado com sucesso!", "success")

    except SQLAlchemyError as erro:
        db.session.rollback()
        flash(f"Erro ao criar post: {erro}", "danger")

    return redirect(url_for("posts.feed"))


@posts_bp.route("/novo-post", methods=["GET", "POST"])
@login_required
def novo_post():
    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para criar posts.", "danger")
        return redirect(url_for("posts.feed"))

    if request.method == "POST":
        conteudo = request.form.get("conteudo", "").strip()

        if not conteudo:
            flash("O conteúdo do post não pode estar vazio.", "warning")
            return redirect(url_for("posts.novo_post"))

        if len(conteudo) > 280:
            flash("O post deve ter no máximo 280 caracteres.", "warning")
            return redirect(url_for("posts.novo_post"))

        try:
            db.session.execute(
                text("CALL sp_criar_post(:usuario_id, :conteudo)"),
                {
                    "usuario_id": current_user.id,
                    "conteudo": conteudo
                }
            )
            db.session.commit()

            flash("Post publicado com sucesso!", "success")
            return redirect(url_for("posts.feed"))

        except SQLAlchemyError as erro:
            db.session.rollback()
            flash(f"Erro ao criar post: {erro}", "danger")
            return redirect(url_for("posts.novo_post"))

    return render_template("novo_post.html")


@posts_bp.route("/denunciar/<int:post_id>", methods=["GET", "POST"])
@login_required
def denunciar_post(post_id):
    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para denunciar posts.", "danger")
        return redirect(url_for("posts.feed"))

    post = Post.query.get_or_404(post_id)

    if post.status_post != "ativo":
        flash("Não é possível denunciar um post que não está ativo.", "warning")
        return redirect(url_for("posts.feed"))

    if request.method == "POST":
        motivo = request.form.get("motivo", "").strip()

        if not motivo:
            flash("Informe o motivo da denúncia.", "warning")
            return redirect(url_for("posts.denunciar_post", post_id=post_id))

        try:
            db.session.execute(
                text("CALL sp_denunciar_post(:denunciante_id, :post_id, :motivo)"),
                {
                    "denunciante_id": current_user.id,
                    "post_id": post_id,
                    "motivo": motivo
                }
            )
            db.session.commit()

            flash("Denúncia enviada para análise da moderação.", "success")
            return redirect(url_for("posts.feed"))

        except SQLAlchemyError as erro:
            db.session.rollback()
            flash(f"Erro ao registrar denúncia: {erro}", "danger")
            return redirect(url_for("posts.feed"))

    return render_template("denunciar_post.html", post=post)