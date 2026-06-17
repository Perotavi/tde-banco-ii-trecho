import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import Usuario


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
EVIDENCIAS_DIR = Path("evidencias_fluxo_completo")

EMAIL_USUARIO = "pedro@trecho.com"
EMAIL_ALICE = "alice@trecho.com"
EMAIL_MODERADOR = "bruno@trecho.com"
EMAIL_ANALISTA = "carla@trecho.com"
EMAIL_ADMIN = "daniel@trecho.com"
SENHA_PADRAO = "123456"


# ============================================================
# PREPARAÇÃO DO BANCO PARA O FLUXO COMPLETO
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def preparar_banco_para_fluxo_completo():
    """
    Deixa os usuários de teste em estado previsível antes do fluxo.

    O teste principal mexe com procedures e rotas importantes, então aqui
    garantimos senha, status e perfil corretos para não depender de execuções
    antigas do banco.
    """

    app = create_app()

    with app.app_context():
        resetar_usuario(EMAIL_USUARIO, "usuario")
        resetar_usuario(EMAIL_ALICE, "usuario")
        resetar_usuario(EMAIL_MODERADOR, "moderador")
        resetar_usuario(EMAIL_ANALISTA, "analista")
        resetar_usuario(EMAIL_ADMIN, "admin")

        garantir_post_base(EMAIL_USUARIO, "Post base do Pedro para fluxo completo Selenium.")
        garantir_post_base(EMAIL_ALICE, "Post base da Alice para fluxo completo Selenium.")
        garantir_post_base(EMAIL_MODERADOR, "Post base do Bruno moderador para fluxo completo Selenium.")
        garantir_post_base(EMAIL_ADMIN, "Post base do Daniel admin para fluxo completo Selenium.")

        db.session.commit()


def resetar_usuario(email, perfil_nome):
    usuario = Usuario.query.filter_by(email=email).first()
    assert usuario is not None, f"Usuário de teste não encontrado: {email}"

    perfil_id = db.session.execute(
        text("SELECT id FROM perfis WHERE nome = :perfil_nome LIMIT 1"),
        {"perfil_nome": perfil_nome}
    ).scalar()
    assert perfil_id is not None, f"Perfil não encontrado: {perfil_nome}"

    usuario.perfil_id = perfil_id
    usuario.status_conta = "ativo"
    usuario.definir_senha(SENHA_PADRAO)

    if hasattr(usuario, "suspenso_ate"):
        usuario.suspenso_ate = None

    if hasattr(usuario, "motivo_punicao"):
        usuario.motivo_punicao = None

    if hasattr(usuario, "bio") and not usuario.bio:
        usuario.bio = "Bio inicial para testes do Trecho."

    db.session.execute(
        text("""
            DELETE FROM bloqueios
            WHERE bloqueador_id = :usuario_id
               OR bloqueado_id = :usuario_id
        """),
        {"usuario_id": usuario.id}
    )


def garantir_post_base(email, conteudo):
    usuario_id = obter_id_usuario(email)

    existente = db.session.execute(
        text("SELECT id FROM posts WHERE conteudo = :conteudo LIMIT 1"),
        {"conteudo": conteudo}
    ).scalar()

    if existente:
        db.session.execute(
            text("UPDATE posts SET status_post = 'ativo' WHERE id = :post_id"),
            {"post_id": existente}
        )
        return existente

    db.session.execute(
        text("""
            INSERT INTO posts (usuario_id, conteudo, status_post)
            VALUES (:usuario_id, :conteudo, 'ativo')
        """),
        {
            "usuario_id": usuario_id,
            "conteudo": conteudo
        }
    )
    db.session.flush()

    return db.session.execute(text("SELECT LAST_INSERT_ID()" )).scalar()


def app_contexto():
    app = create_app()
    return app.app_context()


def obter_id_usuario(email):
    return db.session.execute(
        text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
        {"email": email}
    ).scalar()


def obter_id_usuario_fora_contexto(email):
    app = create_app()

    with app.app_context():
        return db.session.execute(
            text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email}
        ).scalar()


def criar_post_no_banco(email_autor, conteudo, status="ativo"):
    app = create_app()

    with app.app_context():
        usuario_id = db.session.execute(
            text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email_autor}
        ).scalar()
        assert usuario_id is not None

        db.session.execute(
            text("""
                INSERT INTO posts (usuario_id, conteudo, status_post)
                VALUES (:usuario_id, :conteudo, :status)
            """),
            {
                "usuario_id": usuario_id,
                "conteudo": conteudo,
                "status": status
            }
        )
        db.session.commit()

        return db.session.execute(
            text("""
                SELECT id
                FROM posts
                WHERE conteudo = :conteudo
                ORDER BY id DESC
                LIMIT 1
            """),
            {"conteudo": conteudo}
        ).scalar()


def criar_denuncia_no_banco(post_id, denunciante_email, motivo):
    app = create_app()

    with app.app_context():
        denunciante_id = db.session.execute(
            text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": denunciante_email}
        ).scalar()
        assert denunciante_id is not None

        db.session.execute(
            text("DELETE FROM denuncias WHERE post_id = :post_id"),
            {"post_id": post_id}
        )

        db.session.execute(
            text("""
                INSERT INTO denuncias (post_id, denunciante_id, motivo, status_denuncia)
                VALUES (:post_id, :denunciante_id, :motivo, 'pendente')
            """),
            {
                "post_id": post_id,
                "denunciante_id": denunciante_id,
                "motivo": motivo
            }
        )
        db.session.commit()


def obter_post_por_conteudo(conteudo):
    app = create_app()

    with app.app_context():
        return db.session.execute(
            text("""
                SELECT id, usuario_id, conteudo, status_post
                FROM posts
                WHERE conteudo = :conteudo
                ORDER BY id DESC
                LIMIT 1
            """),
            {"conteudo": conteudo}
        ).mappings().first()


def obter_status_usuario(email):
    app = create_app()

    with app.app_context():
        return db.session.execute(
            text("SELECT status_conta FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email}
        ).scalar()


def obter_perfil_usuario(email):
    app = create_app()

    with app.app_context():
        return db.session.execute(
            text("""
                SELECT p.nome
                FROM usuarios u
                INNER JOIN perfis p ON u.perfil_id = p.id
                WHERE u.email = :email
                LIMIT 1
            """),
            {"email": email}
        ).scalar()


def obter_status_post(post_id):
    app = create_app()

    with app.app_context():
        return db.session.execute(
            text("SELECT status_post FROM posts WHERE id = :post_id LIMIT 1"),
            {"post_id": post_id}
        ).scalar()


def contar_comentarios(post_id, conteudo=None):
    app = create_app()

    with app.app_context():
        if conteudo:
            return db.session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM comentarios
                    WHERE post_id = :post_id
                      AND conteudo = :conteudo
                      AND status_comentario = 'ativo'
                """),
                {
                    "post_id": post_id,
                    "conteudo": conteudo
                }
            ).scalar()

        return db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM comentarios
                WHERE post_id = :post_id
                  AND status_comentario = 'ativo'
            """),
            {"post_id": post_id}
        ).scalar()


def contar_curtidas(post_id, email):
    app = create_app()

    with app.app_context():
        usuario_id = db.session.execute(
            text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email}
        ).scalar()

        return db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM curtidas
                WHERE post_id = :post_id
                  AND usuario_id = :usuario_id
            """),
            {
                "post_id": post_id,
                "usuario_id": usuario_id
            }
        ).scalar()


def contar_denuncias(post_id, denunciante_email):
    app = create_app()

    with app.app_context():
        denunciante_id = db.session.execute(
            text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": denunciante_email}
        ).scalar()

        return db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM denuncias
                WHERE post_id = :post_id
                  AND denunciante_id = :denunciante_id
            """),
            {
                "post_id": post_id,
                "denunciante_id": denunciante_id
            }
        ).scalar()


def contar_bloqueio(email_bloqueador, email_bloqueado):
    app = create_app()

    with app.app_context():
        bloqueador_id = db.session.execute(
            text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email_bloqueador}
        ).scalar()
        bloqueado_id = db.session.execute(
            text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email_bloqueado}
        ).scalar()

        return db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM bloqueios
                WHERE bloqueador_id = :bloqueador_id
                  AND bloqueado_id = :bloqueado_id
            """),
            {
                "bloqueador_id": bloqueador_id,
                "bloqueado_id": bloqueado_id
            }
        ).scalar()


def desbloquear_usuario_no_banco(email_bloqueador, email_bloqueado):
    """
    Ainda não existe botão/rota de desbloqueio no projeto.
    O fluxo registra essa etapa limpando a relação no banco para permitir
    continuar testando denúncia e moderação depois do bloqueio.
    """

    app = create_app()

    with app.app_context():
        bloqueador_id = db.session.execute(
            text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email_bloqueador}
        ).scalar()
        bloqueado_id = db.session.execute(
            text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
            {"email": email_bloqueado}
        ).scalar()

        db.session.execute(
            text("""
                DELETE FROM bloqueios
                WHERE bloqueador_id = :bloqueador_id
                  AND bloqueado_id = :bloqueado_id
            """),
            {
                "bloqueador_id": bloqueador_id,
                "bloqueado_id": bloqueado_id
            }
        )
        db.session.commit()


def definir_status_usuario(email, status, suspenso_ate=None, motivo=None):
    app = create_app()

    with app.app_context():
        db.session.execute(
            text("""
                UPDATE usuarios
                SET status_conta = :status,
                    suspenso_ate = :suspenso_ate,
                    motivo_punicao = :motivo
                WHERE email = :email
            """),
            {
                "status": status,
                "suspenso_ate": suspenso_ate,
                "motivo": motivo,
                "email": email
            }
        )
        db.session.commit()


def contar_logs_moderacao(email_alvo=None, acao_like=None):
    app = create_app()

    with app.app_context():
        if email_alvo:
            usuario_id = db.session.execute(
                text("SELECT id FROM usuarios WHERE email = :email LIMIT 1"),
                {"email": email_alvo}
            ).scalar()

            return db.session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM logs_moderacao
                    WHERE usuario_alvo_id = :usuario_id
                      AND (:acao_like IS NULL OR acao LIKE :acao_like)
                """),
                {
                    "usuario_id": usuario_id,
                    "acao_like": acao_like
                }
            ).scalar()

        return db.session.execute(text("SELECT COUNT(*) FROM logs_moderacao")).scalar()


# ============================================================
# CONFIGURAÇÃO DO WEBDRIVER
# ============================================================

@pytest.fixture(scope="session")
def driver():
    EVIDENCIAS_DIR.mkdir(exist_ok=True)

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=1366,900")
        options.add_argument("--disable-save-password-bubble")
        options.add_argument("--disable-features=PasswordLeakDetection,AutofillServerCommunication")
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
            "safebrowsing.enabled": False,
        })
        navegador = webdriver.Chrome(options=options)

    except WebDriverException:
        options = webdriver.FirefoxOptions()
        options.add_argument("--width=1366")
        options.add_argument("--height=900")
        options.set_preference("signon.rememberSignons", False)
        options.set_preference("signon.management.page.breach-alerts.enabled", False)
        options.set_preference("signon.autofillForms", False)
        navegador = webdriver.Firefox(options=options)

    time.sleep(1)
    yield navegador
    time.sleep(1)
    navegador.quit()


# ============================================================
# FUNÇÕES AUXILIARES DO SELENIUM
# ============================================================

def pausar(segundos=0.6):
    time.sleep(segundos)


def esperar(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def esperar_body(driver, timeout=10):
    return esperar(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )


def salvar_evidencia(driver, nome):
    pausar()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = EVIDENCIAS_DIR / f"{nome}_{timestamp}.png"
    driver.save_screenshot(str(caminho))
    pausar()


def fechar_modais(driver):
    driver.execute_script("""
        document.querySelectorAll('.modal-overlay.active').forEach(function(modal) {
            modal.classList.remove('active');
        });
    """)
    pausar(0.3)


def xpath_literal(texto):
    if "'" not in texto:
        return f"'{texto}'"

    if '"' not in texto:
        return f'"{texto}"'

    partes = texto.split("'")
    return "concat(" + ", \"'\", ".join(f"'{parte}'" for parte in partes) + ")"


def buscar_botao_ou_link_por_texto(driver, texto, timeout=10):
    literal = xpath_literal(texto)
    return esperar(driver, timeout).until(
        EC.element_to_be_clickable((
            By.XPATH,
            f"//button[contains(normalize-space(), {literal})] | //a[contains(normalize-space(), {literal})]"
        ))
    )


def existe_botao_ou_link_visivel(driver, texto):
    """
    Verifica se existe link ou botão visível com determinado texto.

    Não usa page_source porque o HTML pode conter o texto dentro de scripts,
    comentários ou templates, e isso gera falso positivo no teste.
    """

    literal = xpath_literal(texto)
    elementos = driver.find_elements(
        By.XPATH,
        f"//button[contains(normalize-space(), {literal})] | //a[contains(normalize-space(), {literal})]"
    )

    return any(elemento.is_displayed() for elemento in elementos)


def existe_elemento_visivel(driver, by, seletor):
    """
    Verifica se um elemento existe e está visível de verdade no DOM.

    Isso evita falhas como procurar 'campoPostFeed' no page_source, porque
    esse texto pode aparecer em JavaScript mesmo quando o campo não está
    sendo exibido para o usuário.
    """

    elementos = driver.find_elements(by, seletor)
    return any(elemento.is_displayed() for elemento in elementos)


def clicar_texto(driver, texto, timeout=10):
    elemento = buscar_botao_ou_link_por_texto(driver, texto, timeout)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
    pausar(0.3)
    driver.execute_script("arguments[0].click();", elemento)
    pausar()
    return elemento


def encontrar_card_por_texto(driver, texto, timeout=10):
    literal = xpath_literal(texto)
    return esperar(driver, timeout).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//*[self::article or self::section or self::div]"
            "[contains(@class, 'tweet-card') or contains(@class, 'post-card')]"
            f"[contains(., {literal})]"
        ))
    )


def clicar_botao_no_card(driver, card, texto_botao):
    literal = xpath_literal(texto_botao)
    botao = card.find_element(
        By.XPATH,
        f".//button[contains(normalize-space(), {literal})]"
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
    pausar(0.3)
    driver.execute_script("arguments[0].click();", botao)
    pausar()


def abrir_menu_do_card(driver, texto_card):
    card = encontrar_card_por_texto(driver, texto_card)
    botao_menu = card.find_element(By.CSS_SELECTOR, ".tweet-more")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_menu)
    pausar(0.3)
    driver.execute_script("arguments[0].click();", botao_menu)
    pausar()
    return card


def clicar_opcao_menu_do_card(driver, texto_card, opcao):
    card = abrir_menu_do_card(driver, texto_card)
    clicar_botao_no_card(driver, card, opcao)
    return card


def logout(driver):
    driver.get(f"{BASE_URL}/auth/logout")
    esperar_body(driver)
    fechar_modais(driver)


def login(driver, email, senha=SENHA_PADRAO, sucesso=True, nome_evidencia=None):
    logout(driver)

    driver.get(f"{BASE_URL}/auth/login")
    esperar_body(driver)

    campo_email = esperar(driver).until(EC.presence_of_element_located((By.NAME, "email")))
    campo_email.clear()
    campo_email.send_keys(email)

    campo_senha = driver.find_element(By.NAME, "senha")
    campo_senha.clear()
    campo_senha.send_keys(senha)

    salvar_evidencia(driver, nome_evidencia or f"login_{email.replace('@', '_').replace('.', '_')}")

    botao = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    driver.execute_script("arguments[0].click();", botao)
    esperar_body(driver)
    pausar()

    if sucesso:
        assert "E-mail ou senha inválidos" not in driver.page_source
        assert "senha inválidos" not in driver.page_source

    return driver.page_source


def preencher_e_enviar_post(driver, conteudo):
    campo = esperar(driver).until(EC.presence_of_element_located((By.ID, "campoPostFeed")))

    driver.execute_script("""
        const campo = document.getElementById('campoPostFeed');
        const botao = document.getElementById('botaoPostarFeed');

        campo.value = arguments[0];
        campo.dispatchEvent(new Event('input', { bubbles: true }));

        if (botao) {
            botao.disabled = false;
        }
    """, conteudo)

    salvar_evidencia(driver, "usuario_post_preenchido")

    driver.execute_script("""
        const campo = document.getElementById('campoPostFeed');
        const form = campo.closest('form');
        form.submit();
    """)
    esperar_body(driver)
    pausar()


def editar_post_pelo_feed(driver, conteudo_original, conteudo_editado):
    clicar_opcao_menu_do_card(driver, conteudo_original, "Editar post")

    modal = esperar(driver).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-overlay.active"))
    )
    textarea = modal.find_element(By.NAME, "conteudo")
    textarea.clear()
    textarea.send_keys(conteudo_editado)

    salvar_evidencia(driver, "usuario_editando_post")

    botao = modal.find_element(By.CSS_SELECTOR, "button[type='submit']")
    driver.execute_script("arguments[0].click();", botao)
    esperar_body(driver)
    pausar()


def editar_bio_perfil(driver, nova_bio):
    driver.get(f"{BASE_URL}/perfil/pedro")
    esperar_body(driver)

    clicar_texto(driver, "Editar perfil")

    modal = esperar(driver).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-overlay.active"))
    )
    campo_bio = modal.find_element(By.NAME, "bio")
    campo_bio.clear()
    campo_bio.send_keys(nova_bio)

    salvar_evidencia(driver, "usuario_editando_bio_perfil")

    form = modal.find_element(By.CSS_SELECTOR, "form")
    driver.execute_script("arguments[0].submit();", form)
    esperar_body(driver)
    pausar()


def comentar_post(driver, post_id, comentario):
    driver.get(f"{BASE_URL}/post/{post_id}")
    esperar_body(driver)

    campo = esperar(driver).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name='conteudo']"))
    )
    campo.clear()
    campo.send_keys(comentario)

    salvar_evidencia(driver, "usuario_comentando_post")

    form = campo.find_element(By.XPATH, "./ancestor::form")
    driver.execute_script("arguments[0].submit();", form)
    esperar_body(driver)
    pausar()


def curtir_post(driver, post_id):
    driver.get(f"{BASE_URL}/post/{post_id}")
    esperar_body(driver)

    botao = esperar(driver).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".like-button"))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
    pausar(0.3)

    salvar_evidencia(driver, "usuario_antes_curtir_post")

    driver.execute_script("arguments[0].click();", botao)
    esperar_body(driver)
    pausar()


def denunciar_post(driver, post_id, motivo, evidencia):
    driver.get(f"{BASE_URL}/denunciar/{post_id}")
    esperar_body(driver)

    campo = esperar(driver).until(EC.presence_of_element_located((By.NAME, "motivo")))
    campo.clear()
    campo.send_keys(motivo)

    salvar_evidencia(driver, evidencia)

    botao = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    driver.execute_script("arguments[0].click();", botao)
    esperar_body(driver)
    pausar()


def bloquear_usuario_pelo_post(driver, post_id, conteudo_card):
    driver.get(f"{BASE_URL}/post/{post_id}")
    esperar_body(driver)
    clicar_opcao_menu_do_card(driver, conteudo_card, "Bloquear usuário")
    esperar_body(driver)
    pausar()


def remover_post_na_moderacao(driver, conteudo_post):
    driver.get(f"{BASE_URL}/moderacao/")
    esperar_body(driver)
    assert "Painel de moderação" in driver.page_source

    card = encontrar_card_por_texto(driver, conteudo_post)
    salvar_evidencia(driver, "moderador_visualiza_denuncia_para_remover")
    clicar_botao_no_card(driver, card, "Remover post")
    esperar_body(driver)
    pausar()


def suspender_usuario_pelo_perfil(driver, username, horas=24):
    driver.get(f"{BASE_URL}/perfil/{username}")
    esperar_body(driver)

    menu = esperar(driver).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".profile-main-menu-button-trecho"))
    )
    driver.execute_script("arguments[0].click();", menu)
    pausar()

    clicar_texto(driver, "Suspender usuário")

    modal = esperar(driver).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-overlay.active"))
    )

    campo_horas = modal.find_element(By.NAME, "duracao_horas")
    campo_horas.clear()
    campo_horas.send_keys(str(horas))

    salvar_evidencia(driver, f"moderador_suspende_{username}")

    form = modal.find_element(By.CSS_SELECTOR, "form")
    driver.execute_script("arguments[0].submit();", form)
    esperar_body(driver)
    pausar()


def banir_usuario_pelo_perfil(driver, username):
    driver.get(f"{BASE_URL}/perfil/{username}")
    esperar_body(driver)

    menu = esperar(driver).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".profile-main-menu-button-trecho"))
    )
    driver.execute_script("arguments[0].click();", menu)
    pausar()

    salvar_evidencia(driver, f"menu_perfil_{username}_antes_banir")

    clicar_texto(driver, "Banir usuário")
    esperar_body(driver)
    pausar()


def reativar_usuario_pelo_perfil(driver, username):
    driver.get(f"{BASE_URL}/perfil/{username}")
    esperar_body(driver)

    menu = esperar(driver).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".profile-main-menu-button-trecho"))
    )
    driver.execute_script("arguments[0].click();", menu)
    pausar()

    salvar_evidencia(driver, f"admin_menu_perfil_{username}_reativar")

    if "Remover suspensão" in driver.page_source:
        clicar_texto(driver, "Remover suspensão")
    else:
        clicar_texto(driver, "Reativar usuário")

    esperar_body(driver)
    pausar()


def promover_usuario_para_moderador(driver, username):
    driver.get(f"{BASE_URL}/perfil/{username}")
    esperar_body(driver)

    menu = esperar(driver).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".profile-main-menu-button-trecho"))
    )
    driver.execute_script("arguments[0].click();", menu)
    pausar()

    salvar_evidencia(driver, f"admin_menu_perfil_{username}_promover")

    clicar_texto(driver, "Tornar moderador")
    esperar_body(driver)
    pausar()


def validar_suspenso_nao_publica_nem_comenta(driver, post_id_para_tentar_comentar):
    driver.get(BASE_URL)
    esperar_body(driver)

    assert "suspensa" in driver.page_source or "suspenso" in driver.page_source

    campos = driver.find_elements(By.ID, "campoPostFeed")
    assert len(campos) == 0 or campos[0].get_attribute("disabled") is not None

    botoes_postar = driver.find_elements(By.ID, "botaoPostarFeed")
    assert len(botoes_postar) == 0 or botoes_postar[0].get_attribute("disabled") is not None

    salvar_evidencia(driver, "usuario_suspenso_feed_postagem_desativada")

    driver.get(f"{BASE_URL}/post/{post_id_para_tentar_comentar}")
    esperar_body(driver)

    assert "Você não pode comentar" in driver.page_source or "suspensa" in driver.page_source

    textarea_desativado = driver.find_elements(By.CSS_SELECTOR, "textarea[disabled]")
    assert len(textarea_desativado) > 0

    salvar_evidencia(driver, "usuario_suspenso_comentario_desativado")


def validar_analista(driver):
    login(driver, EMAIL_ANALISTA, nome_evidencia="analista_login")

    driver.get(BASE_URL)
    esperar_body(driver)

    # O analista pode visualizar o feed, mas não deve ter campo de postagem.
    # Não usamos page_source aqui porque o texto "campoPostFeed" pode aparecer
    # dentro de JavaScript do template mesmo sem o campo estar disponível.
    assert not existe_elemento_visivel(driver, By.ID, "campoPostFeed")
    assert not existe_elemento_visivel(driver, By.ID, "botaoPostarFeed")
    assert not existe_botao_ou_link_visivel(driver, "Postar")
    assert not existe_botao_ou_link_visivel(driver, "Novo trecho")

    # O analista deve ver relatórios, mas não deve ver atalhos de moderação/admin.
    assert existe_botao_ou_link_visivel(driver, "Relatórios")
    assert not existe_botao_ou_link_visivel(driver, "Moderação")
    assert not existe_botao_ou_link_visivel(driver, "Administração")

    salvar_evidencia(driver, "analista_feed_sem_acoes_restritas")

    driver.get(f"{BASE_URL}/relatorios/")
    esperar_body(driver)

    assert "Relatórios" in driver.page_source
    assert "Ranking de posts por engajamento" in driver.page_source
    assert "Usuários por perfil" in driver.page_source
    assert "Denúncias por status" in driver.page_source

    salvar_evidencia(driver, "analista_relatorios")

    driver.get(f"{BASE_URL}/moderacao/")
    esperar_body(driver)
    assert "Painel de moderação" not in driver.page_source

    driver.get(f"{BASE_URL}/admin/")
    esperar_body(driver)
    assert "Usuários cadastrados" not in driver.page_source
    assert "Últimos logins" not in driver.page_source

    salvar_evidencia(driver, "analista_rotas_restritas_bloqueadas")


# ============================================================
# FLUXO COMPLETO PEDIDO
# ============================================================

def test_fluxo_completo_trecho_procedures_e_papeis(driver):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    post_pedro_original = f"Fluxo completo {timestamp} - post inicial do Pedro"
    post_pedro_editado = f"Fluxo completo {timestamp} - post editado do Pedro"
    bio_pedro = f"Bio atualizada pelo fluxo completo Selenium {timestamp}"

    post_alice_interacao = f"Fluxo completo {timestamp} - post da Alice para interação"
    post_alice_denuncia_moderacao = f"Fluxo completo {timestamp} - post da Alice para remoção na moderação"
    post_pedro_moderacao_alice = f"Fluxo completo {timestamp} - post do Pedro para Alice moderadora remover"

    post_alice_interacao_id = criar_post_no_banco(EMAIL_ALICE, post_alice_interacao)
    post_alice_denuncia_moderacao_id = criar_post_no_banco(EMAIL_ALICE, post_alice_denuncia_moderacao)
    criar_denuncia_no_banco(
        post_alice_denuncia_moderacao_id,
        EMAIL_USUARIO,
        "Denúncia criada para o fluxo completo de moderação."
    )

    # 1) Convidado visualiza o feed e tenta interagir.
    logout(driver)
    driver.get(BASE_URL)
    esperar_body(driver)
    assert "Trecho" in driver.page_source
    salvar_evidencia(driver, "01_convidado_visualiza_feed")

    botao_interacao = esperar(driver).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".like-button, .tweet-action-button"))
    )
    driver.execute_script("arguments[0].click();", botao_interacao)
    pausar()

    assert "Entre para interagir" in driver.page_source
    assert "Criar usuário" in driver.page_source
    assert "Entrar" in driver.page_source
    salvar_evidencia(driver, "02_convidado_modal_entre_para_interagir")

    # 2) Tenta entrar com senha errada e depois com senha correta.
    driver.get(f"{BASE_URL}/auth/login")
    esperar_body(driver)

    driver.find_element(By.NAME, "email").send_keys(EMAIL_USUARIO)
    driver.find_element(By.NAME, "senha").send_keys("senha_errada")
    salvar_evidencia(driver, "03_login_senha_errada_preenchido")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    esperar_body(driver)

    assert "inválid" in driver.page_source.lower() or "senha" in driver.page_source.lower()
    salvar_evidencia(driver, "04_login_senha_errada_bloqueado")

    login(driver, EMAIL_USUARIO, nome_evidencia="05_login_usuario_correto")

    # 3) Usuário comum cria post.
    preencher_e_enviar_post(driver, post_pedro_original)
    esperar(driver).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), post_pedro_original))
    assert obter_post_por_conteudo(post_pedro_original) is not None
    salvar_evidencia(driver, "06_usuario_criou_post")

    # 4) Edita post pelo modal/menu do próprio post.
    editar_post_pelo_feed(driver, post_pedro_original, post_pedro_editado)
    esperar(driver).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), post_pedro_editado))
    assert obter_post_por_conteudo(post_pedro_editado) is not None
    salvar_evidencia(driver, "07_usuario_editou_post")

    # 5) Abre notificações e perfil.
    driver.get(f"{BASE_URL}/notificacoes/")
    esperar_body(driver)
    assert "Notificações" in driver.page_source
    salvar_evidencia(driver, "08_usuario_abriu_notificacoes")

    driver.get(f"{BASE_URL}/perfil/pedro")
    esperar_body(driver)
    assert "@pedro" in driver.page_source
    salvar_evidencia(driver, "09_usuario_abriu_perfil")

    # 6) Edita bio do perfil.
    editar_bio_perfil(driver, bio_pedro)
    driver.get(f"{BASE_URL}/perfil/pedro")
    esperar_body(driver)
    assert bio_pedro in driver.page_source
    salvar_evidencia(driver, "10_usuario_editou_bio")

    # 7) Comenta post, curte post e denuncia post.
    comentario = f"Comentário do fluxo completo {timestamp}"
    comentar_post(driver, post_alice_interacao_id, comentario)
    assert contar_comentarios(post_alice_interacao_id, comentario) == 1
    salvar_evidencia(driver, "11_usuario_comentou_post")

    curtir_post(driver, post_alice_interacao_id)
    assert contar_curtidas(post_alice_interacao_id, EMAIL_USUARIO) == 1
    salvar_evidencia(driver, "12_usuario_curtiu_post")

    denunciar_post(
        driver,
        post_alice_interacao_id,
        "Denúncia do primeiro post da Alice no fluxo completo.",
        "13_usuario_denuncia_primeiro_post"
    )
    assert contar_denuncias(post_alice_interacao_id, EMAIL_USUARIO) >= 1

    # 8) Bloqueia Alice, desbloqueia pelo banco, depois denuncia outro post.
    bloquear_usuario_pelo_post(driver, post_alice_interacao_id, post_alice_interacao)
    assert contar_bloqueio(EMAIL_USUARIO, EMAIL_ALICE) == 1
    salvar_evidencia(driver, "14_usuario_bloqueou_alice")

    desbloquear_usuario_no_banco(EMAIL_USUARIO, EMAIL_ALICE)
    assert contar_bloqueio(EMAIL_USUARIO, EMAIL_ALICE) == 0
    driver.get(BASE_URL)
    esperar_body(driver)
    assert post_alice_interacao in driver.page_source or "Feed" in driver.page_source
    salvar_evidencia(driver, "15_usuario_desbloqueado_por_banco")

    denunciar_post(
        driver,
        post_alice_denuncia_moderacao_id,
        "Denúncia do segundo post da Alice para a tela de moderação.",
        "16_usuario_denuncia_post_para_moderacao"
    )
    assert contar_denuncias(post_alice_denuncia_moderacao_id, EMAIL_USUARIO) >= 1

    logout(driver)

    # 9) Moderador acessa moderação e remove post denunciado.
    login(driver, EMAIL_MODERADOR, nome_evidencia="17_moderador_login")
    remover_post_na_moderacao(driver, post_alice_denuncia_moderacao)
    assert obter_status_post(post_alice_denuncia_moderacao_id) == "removido"
    salvar_evidencia(driver, "18_moderador_removeu_post")

    # 10) Moderador acessa perfil da Alice e suspende usuária.
    suspender_usuario_pelo_perfil(driver, "alice", horas=24)
    assert obter_status_usuario(EMAIL_ALICE) == "suspenso"
    assert contar_logs_moderacao(EMAIL_ALICE) >= 1
    salvar_evidencia(driver, "19_moderador_suspendeu_alice")

    logout(driver)

    # 11) Alice suspensa consegue logar, mas não consegue postar nem comentar.
    login(driver, EMAIL_ALICE, nome_evidencia="20_alice_suspensa_login")
    validar_suspenso_nao_publica_nem_comenta(driver, post_alice_interacao_id)
    logout(driver)

    # 12) Moderador bane Alice.
    login(driver, EMAIL_MODERADOR, nome_evidencia="21_moderador_login_para_banir")
    banir_usuario_pelo_perfil(driver, "alice")
    assert obter_status_usuario(EMAIL_ALICE) == "banido"
    salvar_evidencia(driver, "22_moderador_baniu_alice")
    logout(driver)

    # 13) Alice banida não consegue logar.
    login(driver, EMAIL_ALICE, sucesso=False, nome_evidencia="23_alice_banida_tenta_login")
    assert "banida" in driver.page_source.lower() or "banido" in driver.page_source.lower()
    salvar_evidencia(driver, "24_alice_banida_bloqueada_no_login")

    # 14) Analista faz ações permitidas e não acessa áreas restritas.
    validar_analista(driver)
    logout(driver)

    # 15) Admin acessa administração, reativa Alice e promove para moderadora.
    login(driver, EMAIL_ADMIN, nome_evidencia="25_admin_login")

    driver.get(f"{BASE_URL}/admin/")
    esperar_body(driver)
    assert "Administração" in driver.page_source
    assert EMAIL_ALICE in driver.page_source
    salvar_evidencia(driver, "26_admin_abriu_administracao")

    reativar_usuario_pelo_perfil(driver, "alice")
    assert obter_status_usuario(EMAIL_ALICE) == "ativo"
    salvar_evidencia(driver, "27_admin_reativou_alice")

    promover_usuario_para_moderador(driver, "alice")
    assert obter_perfil_usuario(EMAIL_ALICE) == "moderador"
    salvar_evidencia(driver, "28_admin_promoveu_alice_moderadora")

    logout(driver)

    # 16) Alice, agora moderadora, faz uma ação real de moderação.
    post_pedro_moderacao_alice_id = criar_post_no_banco(EMAIL_USUARIO, post_pedro_moderacao_alice)
    criar_denuncia_no_banco(
        post_pedro_moderacao_alice_id,
        EMAIL_ADMIN,
        "Denúncia criada para validar Alice promovida como moderadora."
    )

    login(driver, EMAIL_ALICE, nome_evidencia="29_alice_promovida_login")

    driver.get(f"{BASE_URL}/moderacao/")
    esperar_body(driver)
    assert "Painel de moderação" in driver.page_source
    assert post_pedro_moderacao_alice in driver.page_source
    salvar_evidencia(driver, "30_alice_promovida_acessa_moderacao")

    remover_post_na_moderacao(driver, post_pedro_moderacao_alice)
    assert obter_status_post(post_pedro_moderacao_alice_id) == "removido"
    salvar_evidencia(driver, "31_alice_promovida_removeu_post")

    # Limpeza mínima para não deixar Alice como moderadora em próximos testes.
    definir_status_usuario(EMAIL_ALICE, "ativo", None, None)
    app = create_app()
    with app.app_context():
        perfil_usuario_id = db.session.execute(
            text("SELECT id FROM perfis WHERE nome = 'usuario' LIMIT 1")
        ).scalar()
        db.session.execute(
            text("UPDATE usuarios SET perfil_id = :perfil_id WHERE email = :email"),
            {
                "perfil_id": perfil_usuario_id,
                "email": EMAIL_ALICE
            }
        )
        db.session.commit()

    salvar_evidencia(driver, "32_fluxo_completo_finalizado")
