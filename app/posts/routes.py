from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Post


# Blueprint responsável por feed, posts, curtidas, comentários,
# denúncia, bloqueio, edição e ações rápidas do menu de 3 pontinhos.
posts_bp = Blueprint("posts", __name__)


def redirecionar_para_origem(origem="feed", post_id=None, username=None):
    """
    Redireciona o usuário para a tela correta depois de uma ação.

    Isso evita o problema de:
    - curtir no perfil e ir para detalhes do post;
    - comentar no perfil e ir para detalhes do post;
    - editar post no perfil e voltar para o feed.
    """

    if origem == "post" and post_id:
        return redirect(url_for("posts.ver_post", post_id=post_id))

    if origem == "perfil":
        if username:
            return redirect(url_for("perfil.visualizar_perfil", username=username))

        if current_user.is_authenticated:
            return redirect(url_for("perfil.visualizar_perfil", username=current_user.username))

    return redirect(url_for("posts.feed"))


def usuario_impedido_de_publicar():
    """
    Verifica se o usuário não pode publicar/comentar.

    Política definida no Trecho:
    - usuário suspenso pode logar, visualizar, curtir, denunciar, bloquear e editar perfil;
    - usuário suspenso não pode criar posts nem comentar;
    - usuário banido não deveria estar logado, mas a verificação fica por segurança.
    """

    return current_user.status_conta in ["suspenso", "banido"]


def mensagem_bloqueio_publicacao():
    """
    Retorna uma mensagem amigável para não exibir erro bruto vindo do banco.
    """

    if current_user.status_conta == "suspenso":
        if current_user.suspenso_ate:
            return (
                f"Sua conta está suspensa até {current_user.suspenso_ate}. "
                "Durante esse período você não pode publicar nem comentar."
            )

        return "Sua conta está suspensa. Durante esse período você não pode publicar nem comentar."

    if current_user.status_conta == "banido":
        return "Sua conta está banida e não pode realizar publicações ou comentários."

    return "Sua conta não pode realizar esta ação."


@posts_bp.route("/")
def feed():
    """
    Mostra o feed principal.

    O feed mostra os posts e contadores.
    Comentários aparecem apenas na tela individual do post.
    """

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
                u.foto_perfil_url AS autor_foto_perfil_url,

                perfil_autor.nome AS autor_perfil,

                COUNT(DISTINCT curt.id) AS total_curtidas,
                COUNT(DISTINCT c.id) AS total_comentarios,

                MAX(
                    CASE
                        WHEN curt.usuario_id = :usuario_logado_id THEN 1
                        ELSE 0
                    END
                ) AS usuario_curtiu

            FROM posts p
            INNER JOIN usuarios u ON p.usuario_id = u.id
            INNER JOIN perfis perfil_autor ON u.perfil_id = perfil_autor.id

            LEFT JOIN curtidas curt ON p.id = curt.post_id
            LEFT JOIN comentarios c
                ON p.id = c.post_id
                AND c.status_comentario = 'ativo'

            WHERE p.status_post = 'ativo'

              AND NOT EXISTS (
                    SELECT 1
                    FROM bloqueios b
                    WHERE
                        (
                            b.bloqueador_id = :usuario_logado_id
                            AND b.bloqueado_id = p.usuario_id
                        )
                        OR
                        (
                            b.bloqueador_id = p.usuario_id
                            AND b.bloqueado_id = :usuario_logado_id
                        )
              )

            GROUP BY
                p.id,
                p.usuario_id,
                p.conteudo,
                p.status_post,
                p.data_publicacao,
                p.data_atualizacao,
                u.nome,
                u.username,
                u.foto_perfil_url,
                perfil_autor.nome

            ORDER BY p.data_publicacao DESC
        """),
        {"usuario_logado_id": usuario_logado_id}
    ).mappings().all()

    return render_template("feed.html", posts=posts)


@posts_bp.route("/post/<int:post_id>")
def ver_post(post_id):
    """
    Mostra a tela individual de um post.
    """

    usuario_logado_id = current_user.id if current_user.is_authenticated else 0

    post = db.session.execute(
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
                u.foto_perfil_url AS autor_foto_perfil_url,

                perfil_autor.nome AS autor_perfil,

                COUNT(DISTINCT curt.id) AS total_curtidas,
                COUNT(DISTINCT c.id) AS total_comentarios,

                MAX(
                    CASE
                        WHEN curt.usuario_id = :usuario_logado_id THEN 1
                        ELSE 0
                    END
                ) AS usuario_curtiu

            FROM posts p
            INNER JOIN usuarios u ON p.usuario_id = u.id
            INNER JOIN perfis perfil_autor ON u.perfil_id = perfil_autor.id

            LEFT JOIN curtidas curt ON p.id = curt.post_id
            LEFT JOIN comentarios c
                ON p.id = c.post_id
                AND c.status_comentario = 'ativo'

            WHERE p.id = :post_id
              AND p.status_post = 'ativo'

              AND NOT EXISTS (
                    SELECT 1
                    FROM bloqueios b
                    WHERE
                        (
                            b.bloqueador_id = :usuario_logado_id
                            AND b.bloqueado_id = p.usuario_id
                        )
                        OR
                        (
                            b.bloqueador_id = p.usuario_id
                            AND b.bloqueado_id = :usuario_logado_id
                        )
              )

            GROUP BY
                p.id,
                p.usuario_id,
                p.conteudo,
                p.status_post,
                p.data_publicacao,
                p.data_atualizacao,
                u.nome,
                u.username,
                u.foto_perfil_url,
                perfil_autor.nome
        """),
        {
            "post_id": post_id,
            "usuario_logado_id": usuario_logado_id
        }
    ).mappings().first()

    if not post:
        abort(404)

    comentarios = db.session.execute(
        text("""
            SELECT
                c.id,
                c.post_id,
                c.usuario_id,
                c.conteudo,
                c.data_comentario,

                u.nome AS autor_nome,
                u.username AS autor_username,
                u.foto_perfil_url AS autor_foto_perfil_url

            FROM comentarios c
            INNER JOIN usuarios u ON c.usuario_id = u.id

            WHERE c.post_id = :post_id
              AND c.status_comentario = 'ativo'

            ORDER BY c.data_comentario ASC
        """),
        {"post_id": post_id}
    ).mappings().all()

    return render_template(
        "post_detalhe.html",
        post=post,
        comentarios=comentarios
    )


@posts_bp.route("/criar-post-feed", methods=["POST"])
@login_required
def criar_post_feed():
    """
    Cria um post pelo campo direto do feed.

    Usuário suspenso não pode criar post.
    """

    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para criar posts.", "danger")
        return redirect(url_for("posts.feed"))

    if usuario_impedido_de_publicar():
        flash(mensagem_bloqueio_publicacao(), "warning")
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

    except SQLAlchemyError:
        db.session.rollback()
        flash("Não foi possível publicar o post. Verifique se sua conta está ativa.", "danger")

    return redirect(url_for("posts.feed"))


@posts_bp.route("/novo-post", methods=["GET", "POST"])
@login_required
def novo_post():
    """
    Tela alternativa de criação de post.

    Usuário suspenso não pode criar post.
    """

    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para criar posts.", "danger")
        return redirect(url_for("posts.feed"))

    if usuario_impedido_de_publicar():
        flash(mensagem_bloqueio_publicacao(), "warning")
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

        except SQLAlchemyError:
            db.session.rollback()
            flash("Não foi possível publicar o post. Verifique se sua conta está ativa.", "danger")
            return redirect(url_for("posts.novo_post"))

    return render_template("novo_post.html")


@posts_bp.route("/editar/<int:post_id>", methods=["GET", "POST"])
@login_required
def editar_post(post_id):
    """
    Edita um post do próprio usuário.

    A edição acontece por modal.
    Caso alguém acesse a rota por GET, redireciona para a tela do post.
    """

    post = Post.query.get_or_404(post_id)

    if request.method == "GET":
        return redirect(url_for("posts.ver_post", post_id=post_id))

    novo_conteudo = request.form.get("conteudo", "").strip()
    origem = request.form.get("origem", "feed")
    origem_username = request.form.get("origem_username")

    if post.usuario_id != current_user.id:
        flash("Você só pode editar seus próprios posts.", "danger")
        return redirecionar_para_origem(origem, post_id, origem_username)

    if not novo_conteudo:
        flash("O conteúdo do post não pode estar vazio.", "warning")
        return redirecionar_para_origem(origem, post_id, origem_username)

    if len(novo_conteudo) > 280:
        flash("O post deve ter no máximo 280 caracteres.", "warning")
        return redirecionar_para_origem(origem, post_id, origem_username)

    try:
        db.session.execute(
            text("""
                CALL sp_editar_post(
                    :usuario_id,
                    :post_id,
                    :novo_conteudo
                )
            """),
            {
                "usuario_id": current_user.id,
                "post_id": post_id,
                "novo_conteudo": novo_conteudo
            }
        )
        db.session.commit()

        flash("Post editado com sucesso!", "success")

    except SQLAlchemyError:
        db.session.rollback()
        flash("Erro ao editar post.", "danger")

    return redirecionar_para_origem(origem, post_id, origem_username)


@posts_bp.route("/curtir/<int:post_id>", methods=["POST"])
@login_required
def curtir_post(post_id):
    """
    Curte ou remove a curtida de um post.

    Suspenso pode curtir normalmente.
    """

    origem = request.form.get("origem", "feed")
    origem_username = request.form.get("origem_username")

    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para curtir posts.", "danger")
        return redirecionar_para_origem(origem, post_id, origem_username)

    post = Post.query.get_or_404(post_id)

    if post.status_post != "ativo":
        flash("Não é possível curtir um post que não está ativo.", "warning")
        return redirecionar_para_origem(origem, post_id, origem_username)

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

            # Cria notificação apenas se a pessoa curtir post de outra pessoa.
            if post.usuario_id != current_user.id:
                db.session.execute(
                    text("""
                        INSERT INTO notificacoes (
                            usuario_id,
                            origem_usuario_id,
                            post_id,
                            tipo,
                            mensagem
                        )
                        VALUES (
                            :usuario_id,
                            :origem_usuario_id,
                            :post_id,
                            'curtida',
                            'Seu post recebeu uma nova curtida.'
                        )
                    """),
                    {
                        "usuario_id": post.usuario_id,
                        "origem_usuario_id": current_user.id,
                        "post_id": post_id
                    }
                )

        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        flash("Erro ao curtir post.", "danger")

    return redirecionar_para_origem(origem, post_id, origem_username)


@posts_bp.route("/comentar/<int:post_id>", methods=["POST"])
@login_required
def comentar_post(post_id):
    """
    Cria um comentário em um post.

    Usuário suspenso não pode comentar.
    """

    origem = request.form.get("origem", "post")
    origem_username = request.form.get("origem_username")

    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para comentar.", "danger")
        return redirecionar_para_origem(origem, post_id, origem_username)

    if usuario_impedido_de_publicar():
        flash(mensagem_bloqueio_publicacao(), "warning")
        return redirecionar_para_origem(origem, post_id, origem_username)

    conteudo = request.form.get("conteudo", "").strip()

    if not conteudo:
        flash("O comentário não pode estar vazio.", "warning")
        return redirecionar_para_origem(origem, post_id, origem_username)

    if len(conteudo) > 280:
        flash("O comentário deve ter no máximo 280 caracteres.", "warning")
        return redirecionar_para_origem(origem, post_id, origem_username)

    try:
        db.session.execute(
            text("""
                CALL sp_comentar_post(
                    :usuario_id,
                    :post_id,
                    :conteudo
                )
            """),
            {
                "usuario_id": current_user.id,
                "post_id": post_id,
                "conteudo": conteudo
            }
        )
        db.session.commit()

        flash("Comentário publicado com sucesso!", "success")

    except SQLAlchemyError:
        db.session.rollback()
        flash("Não foi possível comentar. Verifique se sua conta está ativa.", "warning")

    return redirecionar_para_origem(origem, post_id, origem_username)


@posts_bp.route("/denunciar/<int:post_id>", methods=["GET", "POST"])
@login_required
def denunciar_post(post_id):
    """
    Denuncia um post.

    Suspenso pode denunciar normalmente.
    """

    origem = request.form.get("origem", "feed")
    origem_username = request.form.get("origem_username")

    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para denunciar posts.", "danger")
        return redirecionar_para_origem(origem, post_id, origem_username)

    post = Post.query.get_or_404(post_id)

    if post.status_post != "ativo":
        flash("Não é possível denunciar um post que não está ativo.", "warning")
        return redirecionar_para_origem(origem, post_id, origem_username)

    if request.method == "POST":
        motivo = request.form.get("motivo", "").strip()

        if not motivo:
            flash("Informe o motivo da denúncia.", "warning")
            return redirecionar_para_origem(origem, post_id, origem_username)

        try:
            db.session.execute(
                text("""
                    CALL sp_denunciar_post(
                        :denunciante_id,
                        :post_id,
                        :motivo
                    )
                """),
                {
                    "denunciante_id": current_user.id,
                    "post_id": post_id,
                    "motivo": motivo
                }
            )
            db.session.commit()

            flash("Denúncia enviada para análise da moderação.", "success")
            return redirecionar_para_origem(origem, post_id, origem_username)

        except SQLAlchemyError:
            db.session.rollback()
            flash("Erro ao registrar denúncia.", "danger")
            return redirecionar_para_origem(origem, post_id, origem_username)

    return render_template("denunciar_post.html", post=post)


@posts_bp.route("/bloquear-usuario/<int:usuario_id>", methods=["POST"])
@login_required
def bloquear_usuario(usuario_id):
    """
    Bloqueia outro usuário.

    Suspenso pode bloquear normalmente.
    """

    origem = request.form.get("origem", "feed")
    origem_username = request.form.get("origem_username")

    if not current_user.tem_perfil("usuario", "moderador", "admin"):
        flash("Seu perfil não possui permissão para bloquear usuários.", "danger")
        return redirecionar_para_origem(origem, None, origem_username)

    try:
        db.session.execute(
            text("""
                CALL sp_bloquear_usuario(
                    :bloqueador_id,
                    :bloqueado_id
                )
            """),
            {
                "bloqueador_id": current_user.id,
                "bloqueado_id": usuario_id
            }
        )
        db.session.commit()

        flash("Usuário bloqueado com sucesso.", "success")

    except SQLAlchemyError:
        db.session.rollback()
        flash("Erro ao bloquear usuário.", "danger")

    return redirecionar_para_origem(origem, None, origem_username)


@posts_bp.route("/remover-post/<int:post_id>", methods=["POST"])
@login_required
def remover_post_menu(post_id):
    """
    Remove post pelo menu de 3 pontinhos.
    """

    origem = request.form.get("origem", "feed")
    origem_username = request.form.get("origem_username")

    if not current_user.tem_perfil("moderador", "admin"):
        flash("Apenas moderadores e administradores podem remover posts.", "danger")
        return redirecionar_para_origem(origem, post_id, origem_username)

    justificativa = request.form.get(
        "justificativa",
        "Post removido pelo menu de moderação."
    ).strip()

    if not justificativa:
        justificativa = "Post removido pelo menu de moderação."

    try:
        db.session.execute(
            text("""
                CALL sp_moderar_post(
                    :moderador_id,
                    :post_id,
                    'remover',
                    :justificativa
                )
            """),
            {
                "moderador_id": current_user.id,
                "post_id": post_id,
                "justificativa": justificativa
            }
        )
        db.session.commit()

        flash("Post removido com sucesso.", "success")

    except SQLAlchemyError:
        db.session.rollback()
        flash("Erro ao remover post.", "danger")

    return redirecionar_para_origem(origem, post_id, origem_username)


@posts_bp.route("/alterar-status-usuario/<int:usuario_id>/<novo_status>", methods=["POST"])
@login_required
def alterar_status_usuario_menu(usuario_id, novo_status):
    """
    Suspende, bane ou reativa usuário pelo menu.

    A procedure do banco também garante as regras de hierarquia.
    """

    origem = request.form.get("origem", "feed")
    origem_username = request.form.get("origem_username")

    if not current_user.tem_perfil("moderador", "admin"):
        flash("Apenas moderadores e administradores podem alterar status de usuários.", "danger")
        return redirecionar_para_origem(origem, None, origem_username)

    if novo_status not in ["ativo", "suspenso", "banido"]:
        flash("Status inválido.", "danger")
        return redirecionar_para_origem(origem, None, origem_username)

    justificativa = request.form.get("justificativa", "").strip()
    duracao_horas = request.form.get("duracao_horas", "24").strip()

    if not justificativa:
        justificativa = f"Status alterado para {novo_status} pelo menu de moderação."

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

    except SQLAlchemyError:
        db.session.rollback()
        flash("Erro ao alterar status do usuário. Verifique a hierarquia das contas.", "danger")

    return redirecionar_para_origem(origem, None, origem_username)


@posts_bp.route("/alterar-perfil-usuario/<int:usuario_id>/<novo_perfil>", methods=["POST"])
@login_required
def alterar_perfil_usuario_menu(usuario_id, novo_perfil):
    """
    Altera o perfil de um usuário pelo menu de 3 pontinhos.

    Regra:
    - somente admin pode alterar hierarquia;
    - admin não pode alterar o próprio perfil por esse menu;
    - perfis válidos: usuario, moderador, analista, admin;
    - registra a ação em logs_moderacao.
    """

    origem = request.form.get("origem", "feed")
    origem_username = request.form.get("origem_username")
    justificativa = request.form.get("justificativa", "").strip()

    perfis_validos = ["usuario", "moderador", "analista", "admin"]

    if not current_user.tem_perfil("admin"):
        flash("Apenas administradores podem alterar hierarquia de usuários.", "danger")
        return redirecionar_para_origem(origem, None, origem_username)

    if current_user.id == usuario_id:
        flash("Você não pode alterar o próprio perfil por este menu.", "warning")
        return redirecionar_para_origem(origem, None, origem_username)

    if novo_perfil not in perfis_validos:
        flash("Perfil informado é inválido.", "danger")
        return redirecionar_para_origem(origem, None, origem_username)

    if not justificativa:
        justificativa = f"Perfil do usuário alterado para {novo_perfil} pelo administrador."

    try:
        perfil = db.session.execute(
            text("""
                SELECT id
                FROM perfis
                WHERE nome = :nome
                LIMIT 1
            """),
            {"nome": novo_perfil}
        ).mappings().first()

        if not perfil:
            flash("Perfil não encontrado no banco de dados.", "danger")
            return redirecionar_para_origem(origem, None, origem_username)

        db.session.execute(
            text("""
                UPDATE usuarios
                SET perfil_id = :perfil_id
                WHERE id = :usuario_id
            """),
            {
                "perfil_id": perfil.id,
                "usuario_id": usuario_id
            }
        )

        db.session.execute(
            text("""
                INSERT INTO logs_moderacao (
                    moderador_id,
                    usuario_alvo_id,
                    acao,
                    justificativa,
                    data_acao
                )
                VALUES (
                    :moderador_id,
                    :usuario_alvo_id,
                    :acao,
                    :justificativa,
                    NOW()
                )
            """),
            {
                "moderador_id": current_user.id,
                "usuario_alvo_id": usuario_id,
                "acao": f"alteracao_perfil_{novo_perfil}",
                "justificativa": justificativa
            }
        )

        db.session.commit()

        flash(f"Perfil do usuário alterado para {novo_perfil}.", "success")

    except SQLAlchemyError:
        db.session.rollback()
        flash("Erro ao alterar perfil do usuário.", "danger")

    return redirecionar_para_origem(origem, None, origem_username)
