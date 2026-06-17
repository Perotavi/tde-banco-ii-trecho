from datetime import datetime
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Usuario


# Blueprint da tela de perfil.
perfil_bp = Blueprint("perfil", __name__, url_prefix="/perfil")


# Extensões aceitas para foto e capa.
EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "webp", "gif"}


def arquivo_permitido(nome_arquivo):
    """
    Verifica se o arquivo enviado possui uma extensão de imagem permitida.
    """
    if "." not in nome_arquivo:
        return False

    extensao = nome_arquivo.rsplit(".", 1)[1].lower()
    return extensao in EXTENSOES_PERMITIDAS


def salvar_imagem_perfil(arquivo, prefixo):
    """
    Salva a imagem já recortada pelo cropper em app/static/uploads/perfis.

    O banco recebe o caminho relativo gerado pelo Flask, por exemplo:
    /static/uploads/perfis/foto_1_20260617_120000.png
    """

    if not arquivo or arquivo.filename == "":
        return None

    if not arquivo_permitido(arquivo.filename):
        raise ValueError("Formato de imagem inválido. Use png, jpg, jpeg, webp ou gif.")

    pasta_upload = Path(current_app.root_path) / "static" / "uploads" / "perfis"
    pasta_upload.mkdir(parents=True, exist_ok=True)

    nome_original = secure_filename(arquivo.filename)
    extensao = nome_original.rsplit(".", 1)[1].lower()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_final = f"{prefixo}_{current_user.id}_{timestamp}.{extensao}"

    caminho_absoluto = pasta_upload / nome_final
    arquivo.save(caminho_absoluto)

    return url_for("static", filename=f"uploads/perfis/{nome_final}")


@perfil_bp.route("/<username>")
def visualizar_perfil(username):
    """
    Mostra o perfil público de um usuário.

    O template decide o que mostrar dependendo do perfil logado:
    - usuário comum vê nome, @, bio, foto, capa e posts;
    - moderador/admin também veem tipo de perfil e status da conta.
    """

    usuario = Usuario.query.filter_by(username=username).first_or_404()

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

                COUNT(DISTINCT curt.id) AS total_curtidas,
                COUNT(DISTINCT c.id) AS total_comentarios,

                MAX(
                    CASE
                        WHEN curt.usuario_id = :usuario_logado_id THEN 1
                        ELSE 0
                    END
                ) AS usuario_curtiu

            FROM posts p

            LEFT JOIN curtidas curt ON p.id = curt.post_id
            LEFT JOIN comentarios c
                ON p.id = c.post_id
                AND c.status_comentario = 'ativo'

            WHERE p.usuario_id = :usuario_id
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
                p.data_atualizacao

            ORDER BY p.data_publicacao DESC
        """),
        {
            "usuario_id": usuario.id,
            "usuario_logado_id": usuario_logado_id
        }
    ).mappings().all()

    return render_template(
        "perfil.html",
        usuario=usuario,
        posts=posts
    )


@perfil_bp.route("/editar", methods=["GET", "POST"])
@login_required
def editar_perfil():
    """
    Atualiza o próprio perfil.

    O GET apenas redireciona para o perfil, porque agora a edição acontece
    dentro de um modal na própria tela de perfil.
    """

    if request.method == "GET":
        return redirect(url_for("perfil.visualizar_perfil", username=current_user.username))

    bio = request.form.get("bio", "").strip()

    if len(bio) > 280:
        flash("A bio deve ter no máximo 280 caracteres.", "warning")
        return redirect(url_for("perfil.visualizar_perfil", username=current_user.username))

    foto_perfil_url = current_user.foto_perfil_url
    capa_perfil_url = current_user.capa_perfil_url

    try:
        # Recebe as imagens já recortadas pelo cropper do navegador.
        nova_foto = salvar_imagem_perfil(
            request.files.get("foto_perfil_cortada"),
            "foto"
        )

        nova_capa = salvar_imagem_perfil(
            request.files.get("capa_perfil_cortada"),
            "capa"
        )

        if nova_foto:
            foto_perfil_url = nova_foto

        if nova_capa:
            capa_perfil_url = nova_capa

        db.session.execute(
            text("""
                CALL sp_atualizar_perfil_usuario(
                    :usuario_id,
                    :bio,
                    :foto_perfil_url,
                    :capa_perfil_url
                )
            """),
            {
                "usuario_id": current_user.id,
                "bio": bio if bio else None,
                "foto_perfil_url": foto_perfil_url,
                "capa_perfil_url": capa_perfil_url
            }
        )
        db.session.commit()

        flash("Perfil atualizado com sucesso!", "success")

    except ValueError as erro:
        db.session.rollback()
        flash(str(erro), "warning")

    except SQLAlchemyError as erro:
        db.session.rollback()
        flash(f"Erro ao atualizar perfil: {erro}", "danger")

    return redirect(url_for("perfil.visualizar_perfil", username=current_user.username))