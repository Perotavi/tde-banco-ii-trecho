from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Post

posts_bp = Blueprint("posts", __name__)


@posts_bp.route("/")
def feed():
    usuario_logado_id = current_user.id if current_user.is_authenticated else 0

    posts = db.session.execute(
        text("""
            SELECT
                p.id,
                p.usuario_id,
                p.conteudo,
                p.status_post,
                p.data_publicacao,
                p.data_atualizacao,
                u.nome AS autor_nome,
                u.username AS autor_username,
                COUNT(DISTINCT curt.id) AS total_curtidas,
                COUNT(DISTINCT c.id) AS total_comentarios,
                MAX(CASE WHEN curt.usuario_id = :usuario_logado_id THEN 1 ELSE 0 END) AS usuario_curtiu
            FROM posts p
            INNER JOIN usuarios u ON p.usuario_id = u.id
            LEFT JOIN curtidas curt ON p.id = curt.post_id
            LEFT JOIN comentarios c ON p.id = c.post_id AND c.status_comentario = 'ativo'
            WHERE p.status_post = 'ativo'
            GROUP BY
                p.id,
                p.usuario_id,
                p.conteudo,
                p.status_post,
                p.data_publicacao,
                p.data_atualizacao,
                u.nome,
                u.username
            ORDER BY p.data_publicacao DESC
        """),
        {"usuario_logado_id": usuario_logado_id}
    ).mappings().all()

    return render_template("feed.html", posts=posts)


@posts_bp.route("/criar-post-feed", methods=["POST"])
@login_required
def criar_post_feed():
    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para criar posts.", "danger")
        return redirect(url_for("posts.feed"))

    if current_user.status_conta == "suspenso":
        flash("Sua conta está suspensa. Durante esse período você não poderá publicar.", "warning")
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


@posts_bp.route("/curtir/<int:post_id>", methods=["POST"])
@login_required
def curtir_post(post_id):
    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para curtir posts.", "danger")
        return redirect(url_for("posts.feed"))

    if current_user.status_conta == "banido":
        flash("Usuário banido não pode interagir com posts.", "danger")
        return redirect(url_for("posts.feed"))

    post = Post.query.get_or_404(post_id)

    if post.status_post != "ativo":
        flash("Não é possível curtir um post que não está ativo.", "warning")
        return redirect(url_for("posts.feed"))

    try:
        curtida_existente = db.session.execute(
            text("""
                SELECT id
                FROM curtidas
                WHERE post_id = :post_id
                  AND usuario_id = :usuario_id
                LIMIT 1
            """),
            {
                "post_id": post_id,
                "usuario_id": current_user.id
            }
        ).mappings().first()

        if curtida_existente:
            db.session.execute(
                text("""
                    DELETE FROM curtidas
                    WHERE post_id = :post_id
                      AND usuario_id = :usuario_id
                """),
                {
                    "post_id": post_id,
                    "usuario_id": current_user.id
                }
            )
        else:
            db.session.execute(
                text("""
                    INSERT INTO curtidas (post_id, usuario_id)
                    VALUES (:post_id, :usuario_id)
                """),
                {
                    "post_id": post_id,
                    "usuario_id": current_user.id
                }
            )

        db.session.commit()

    except SQLAlchemyError as erro:
        db.session.rollback()
        flash(f"Erro ao curtir post: {erro}", "danger")

    return redirect(url_for("posts.feed"))


@posts_bp.route("/novo-post", methods=["GET", "POST"])
@login_required
def novo_post():
    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para criar posts.", "danger")
        return redirect(url_for("posts.feed"))

    if current_user.status_conta == "suspenso":
        flash("Sua conta está suspensa. Durante esse período você não poderá publicar.", "warning")
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