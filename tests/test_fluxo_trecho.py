import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import Usuario


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
EVIDENCIAS_DIR = Path("evidencias")


# ============================================================
# PREPARAÇÃO DO BANCO PARA OS TESTES
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def preparar_banco_para_testes():
    app = create_app()

    with app.app_context():
        emails_teste = [
            "pedro@trecho.com",
            "alice@trecho.com",
            "bruno@trecho.com",
            "carla@trecho.com",
            "daniel@trecho.com",
        ]

        usuarios = Usuario.query.filter(Usuario.email.in_(emails_teste)).all()

        for usuario in usuarios:
            usuario.status_conta = "ativo"

            if hasattr(usuario, "suspenso_ate"):
                usuario.suspenso_ate = None

            if hasattr(usuario, "motivo_punicao"):
                usuario.motivo_punicao = None

            usuario.definir_senha("123456")

        db.session.commit()

        pedro = Usuario.query.filter_by(email="pedro@trecho.com").first()
        alice = Usuario.query.filter_by(email="alice@trecho.com").first()
        bruno = Usuario.query.filter_by(email="bruno@trecho.com").first()
        admin = Usuario.query.filter_by(email="daniel@trecho.com").first()

        if pedro:
            criar_post_teste(pedro.id, "Post base do Pedro para evidências Selenium.")

        if alice:
            criar_post_teste(alice.id, "Post base da Alice para evidências Selenium.")

        if bruno:
            criar_post_teste(bruno.id, "Post base do Bruno moderador para evidências Selenium.")

        if admin:
            criar_post_teste(admin.id, "Post base do administrador para evidências Selenium.")


def criar_post_teste(usuario_id, conteudo):
    existente = db.session.execute(
        text("""
            SELECT id
            FROM posts
            WHERE conteudo = :conteudo
            LIMIT 1
        """),
        {"conteudo": conteudo}
    ).mappings().first()

    if not existente:
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
        db.session.commit()
    else:
        db.session.execute(
            text("""
                UPDATE posts
                SET status_post = 'ativo'
                WHERE conteudo = :conteudo
            """),
            {"conteudo": conteudo}
        )
        db.session.commit()


def atualizar_status_usuario(email, status, suspenso_ate=None, motivo=None):
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


def obter_status_usuario(email):
    app = create_app()

    with app.app_context():
        return db.session.execute(
            text("""
                SELECT status_conta
                FROM usuarios
                WHERE email = :email
            """),
            {"email": email}
        ).scalar()


def obter_status_post(post_id):
    app = create_app()

    with app.app_context():
        return db.session.execute(
            text("""
                SELECT status_post
                FROM posts
                WHERE id = :post_id
            """),
            {"post_id": post_id}
        ).scalar()


def preparar_post_com_denuncia_para_moderacao(conteudo, autor_email, denunciante_email, motivo):
    app = create_app()

    with app.app_context():
        autor = db.session.execute(
            text("""
                SELECT id
                FROM usuarios
                WHERE email = :email
            """),
            {"email": autor_email}
        ).mappings().first()

        denunciante = db.session.execute(
            text("""
                SELECT id
                FROM usuarios
                WHERE email = :email
            """),
            {"email": denunciante_email}
        ).mappings().first()

        assert autor is not None
        assert denunciante is not None

        db.session.execute(
            text("""
                UPDATE usuarios
                SET status_conta = 'ativo',
                    suspenso_ate = NULL,
                    motivo_punicao = NULL
                WHERE email IN (:autor_email, :denunciante_email)
            """),
            {
                "autor_email": autor_email,
                "denunciante_email": denunciante_email
            }
        )

        post = db.session.execute(
            text("""
                SELECT id
                FROM posts
                WHERE conteudo = :conteudo
                LIMIT 1
            """),
            {"conteudo": conteudo}
        ).mappings().first()

        if not post:
            db.session.execute(
                text("""
                    INSERT INTO posts (usuario_id, conteudo, status_post)
                    VALUES (:usuario_id, :conteudo, 'ativo')
                """),
                {
                    "usuario_id": autor.id,
                    "conteudo": conteudo
                }
            )
            db.session.commit()

            post = db.session.execute(
                text("""
                    SELECT id
                    FROM posts
                    WHERE conteudo = :conteudo
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {"conteudo": conteudo}
            ).mappings().first()
        else:
            db.session.execute(
                text("""
                    UPDATE posts
                    SET status_post = 'ativo'
                    WHERE id = :post_id
                """),
                {"post_id": post.id}
            )

        db.session.execute(
            text("""
                DELETE FROM denuncias
                WHERE post_id = :post_id
            """),
            {"post_id": post.id}
        )

        db.session.execute(
            text("""
                INSERT INTO denuncias (post_id, denunciante_id, motivo, status_denuncia)
                VALUES (:post_id, :denunciante_id, :motivo, 'pendente')
            """),
            {
                "post_id": post.id,
                "denunciante_id": denunciante.id,
                "motivo": motivo
            }
        )

        db.session.commit()

        return post.id


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
        driver = webdriver.Chrome(options=options)

    except WebDriverException:
        options = webdriver.FirefoxOptions()
        options.add_argument("--width=1366")
        options.add_argument("--height=900")
        options.set_preference("signon.rememberSignons", False)
        options.set_preference("signon.management.page.breach-alerts.enabled", False)
        options.set_preference("signon.autofillForms", False)
        driver = webdriver.Firefox(options=options)

    time.sleep(1)

    yield driver

    time.sleep(1)
    driver.quit()


# ============================================================
# FUNÇÕES AUXILIARES DO SELENIUM
# ============================================================

def pausar():
    time.sleep(1)


def salvar_evidencia(driver, nome_teste):
    pausar()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = EVIDENCIAS_DIR / f"{nome_teste}_{timestamp}.png"
    driver.save_screenshot(str(caminho))
    pausar()


def esperar(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def fechar_modais(driver):
    driver.execute_script("""
        document.querySelectorAll('.modal-overlay.active').forEach(function(modal) {
            modal.classList.remove('active');
        });
    """)
    pausar()


def existe_link_ou_botao_visivel(driver, texto):
    elementos = driver.find_elements(
        By.XPATH,
        f"//a[contains(normalize-space(), '{texto}')] | //button[contains(normalize-space(), '{texto}')]"
    )

    for elemento in elementos:
        if elemento.is_displayed():
            return True

    return False


def login(driver, email, senha="123456", fechar_modal=True):
    driver.get(f"{BASE_URL}/auth/logout")
    pausar()

    driver.get(f"{BASE_URL}/auth/login")
    pausar()

    campo_email = esperar(driver).until(
        EC.presence_of_element_located((By.NAME, "email"))
    )
    campo_email.clear()
    campo_email.send_keys(email)
    pausar()

    campo_senha = driver.find_element(By.NAME, "senha")
    campo_senha.clear()
    campo_senha.send_keys(senha)
    pausar()

    salvar_evidencia(driver, f"login_preenchido_{email.replace('@', '_').replace('.', '_')}")

    botao_login = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    botao_login.click()
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    if fechar_modal:
        fechar_modais(driver)

    assert "E-mail ou senha inválidos" not in driver.page_source


def preencher_e_enviar_post(driver, conteudo):
    campo = esperar(driver).until(
        EC.presence_of_element_located((By.ID, "campoPostFeed"))
    )
    pausar()

    driver.execute_script("""
        const campo = document.getElementById('campoPostFeed');
        const botao = document.getElementById('botaoPostarFeed');

        campo.value = arguments[0];
        campo.dispatchEvent(new Event('input', { bubbles: true }));

        if (botao) {
            botao.disabled = false;
        }
    """, conteudo)
    pausar()

    salvar_evidencia(driver, "campo_post_preenchido")

    driver.execute_script("""
        const campo = document.getElementById('campoPostFeed');
        const form = campo.closest('form');
        form.submit();
    """)
    pausar()


def encontrar_card_por_texto(driver, texto):
    return esperar(driver).until(
        EC.presence_of_element_located((
            By.XPATH,
            f"//article[contains(@class, 'post-card') and contains(., \"{texto}\")]"
        ))
    )


def clicar_botao_do_card(driver, card, texto_botao):
    botao = card.find_element(
        By.XPATH,
        f".//button[contains(normalize-space(), '{texto_botao}')]"
    )

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
    pausar()

    driver.execute_script("arguments[0].click();", botao)
    pausar()


def abrir_admin_e_validar_status(driver, email, status):
    driver.get(f"{BASE_URL}/admin/")
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert "Administração" in driver.page_source
    assert email in driver.page_source
    assert status in driver.page_source

    salvar_evidencia(driver, f"admin_mostra_{email.replace('@', '_').replace('.', '_')}_{status}")


# ============================================================
# TESTES SELENIUM PARA EVIDÊNCIAS DO RELATÓRIO
# ============================================================

def test_01_visitante_visualiza_feed_publico(driver):
    driver.get(BASE_URL)
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    fechar_modais(driver)

    assert "Trecho" in driver.page_source

    salvar_evidencia(driver, "test_01_visitante_visualiza_feed_publico")


def test_02_usuario_comum_cria_post_e_visualiza_no_feed(driver):
    atualizar_status_usuario("pedro@trecho.com", "ativo", None, None)

    login(driver, "pedro@trecho.com")

    salvar_evidencia(driver, "test_02_usuario_logado_feed_antes_post")

    conteudo = f"Post criado pelo teste Selenium {datetime.now().strftime('%H%M%S')}"

    preencher_e_enviar_post(driver, conteudo)

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), conteudo)
    )
    pausar()

    assert conteudo in driver.page_source

    salvar_evidencia(driver, "test_02_usuario_comum_criou_post_feed_depois")


def test_03_usuario_comum_curte_post(driver):
    atualizar_status_usuario("pedro@trecho.com", "ativo", None, None)

    login(driver, "pedro@trecho.com")

    fechar_modais(driver)

    salvar_evidencia(driver, "test_03_feed_antes_curtida")

    botao_curtir = esperar(driver).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".like-button"))
    )
    pausar()

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_curtir)
    pausar()

    driver.execute_script("arguments[0].click();", botao_curtir)
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".like-button"))
    )

    assert "❤" in driver.page_source or "♡" in driver.page_source

    salvar_evidencia(driver, "test_03_usuario_comum_curtiu_post")


def test_04_usuario_comum_denuncia_post(driver):
    atualizar_status_usuario("pedro@trecho.com", "ativo", None, None)

    conteudo = f"Post da Alice denunciado pelo usuário comum {datetime.now().strftime('%H%M%S')}"

    post_id = preparar_post_com_denuncia_para_moderacao(
        conteudo=conteudo,
        autor_email="alice@trecho.com",
        denunciante_email="pedro@trecho.com",
        motivo="Denúncia criada para teste."
    )

    login(driver, "pedro@trecho.com")

    driver.get(f"{BASE_URL}/denunciar/{post_id}")
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.NAME, "motivo"))
    )

    salvar_evidencia(driver, "test_04_tela_denunciar_post")

    campo_motivo = driver.find_element(By.NAME, "motivo")
    campo_motivo.clear()
    campo_motivo.send_keys("Denúncia criada automaticamente pelo teste Selenium.")
    pausar()

    salvar_evidencia(driver, "test_04_motivo_denuncia_preenchido")

    botao = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    driver.execute_script("arguments[0].click();", botao)
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert "Denúncia" in driver.page_source or "denúncia" in driver.page_source

    salvar_evidencia(driver, "test_04_denuncia_enviada")


def test_05_analista_acessa_relatorios_e_nao_consegue_postar(driver):
    atualizar_status_usuario("carla@trecho.com", "ativo", None, None)

    login(driver, "carla@trecho.com")

    pausar()

    campos_postagem = driver.find_elements(By.ID, "campoPostFeed")
    assert len(campos_postagem) == 0

    assert not existe_link_ou_botao_visivel(driver, "Postar")
    assert not existe_link_ou_botao_visivel(driver, "Novo post")

    salvar_evidencia(driver, "test_05_analista_feed_sem_area_postagem")

    driver.get(f"{BASE_URL}/relatorios/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Relatórios")
    )

    assert "Ranking de posts por engajamento" in driver.page_source
    assert "Usuários por perfil" in driver.page_source
    assert "Denúncias por status" in driver.page_source

    salvar_evidencia(driver, "test_05_analista_acessou_relatorios")


def test_06_analista_nao_ve_links_restritos_no_menu(driver):
    atualizar_status_usuario("carla@trecho.com", "ativo", None, None)

    login(driver, "carla@trecho.com")

    pausar()

    assert existe_link_ou_botao_visivel(driver, "Relatórios")
    assert not existe_link_ou_botao_visivel(driver, "Moderação")
    assert not existe_link_ou_botao_visivel(driver, "Administração")
    assert not existe_link_ou_botao_visivel(driver, "Novo post")

    campos_postagem = driver.find_elements(By.ID, "campoPostFeed")
    assert len(campos_postagem) == 0

    salvar_evidencia(driver, "test_06_analista_nao_ve_links_restritos_no_menu")


def test_07_analista_nao_acessa_rotas_restritas_por_url(driver):
    atualizar_status_usuario("carla@trecho.com", "ativo", None, None)

    login(driver, "carla@trecho.com")

    driver.get(f"{BASE_URL}/moderacao/")
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert "Painel de moderação" not in driver.page_source
    assert "Acesso restrito" in driver.page_source or "Feed" in driver.page_source or "Trecho" in driver.page_source

    salvar_evidencia(driver, "test_07_analista_bloqueado_moderacao_por_url")

    driver.get(f"{BASE_URL}/admin/")
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert "Administração" not in driver.page_source
    assert "Acesso restrito" in driver.page_source or "Feed" in driver.page_source or "Trecho" in driver.page_source

    salvar_evidencia(driver, "test_07_analista_bloqueado_admin_por_url")


def test_08_moderador_acessa_painel_de_moderacao(driver):
    atualizar_status_usuario("bruno@trecho.com", "ativo", None, None)

    conteudo = f"Post da Alice para painel do moderador {datetime.now().strftime('%H%M%S')}"

    preparar_post_com_denuncia_para_moderacao(
        conteudo=conteudo,
        autor_email="alice@trecho.com",
        denunciante_email="pedro@trecho.com",
        motivo="Denúncia pendente para evidência do painel de moderação."
    )

    login(driver, "bruno@trecho.com")

    driver.get(f"{BASE_URL}/moderacao/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Painel de moderação")
    )

    assert "Painel de moderação" in driver.page_source
    assert conteudo in driver.page_source

    salvar_evidencia(driver, "test_08_moderador_acessou_painel_moderacao")


def test_09_moderador_remove_post_de_usuario_comum_pela_interface(driver):
    atualizar_status_usuario("bruno@trecho.com", "ativo", None, None)
    atualizar_status_usuario("alice@trecho.com", "ativo", None, None)

    conteudo = f"Post da Alice que será removido pelo moderador {datetime.now().strftime('%H%M%S')}"

    post_id = preparar_post_com_denuncia_para_moderacao(
        conteudo=conteudo,
        autor_email="alice@trecho.com",
        denunciante_email="pedro@trecho.com",
        motivo="Denúncia para teste de remoção pelo moderador."
    )

    login(driver, "bruno@trecho.com")

    driver.get(f"{BASE_URL}/moderacao/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Painel de moderação")
    )

    card = encontrar_card_por_texto(driver, conteudo)

    assert "Remover post" in card.text

    salvar_evidencia(driver, "test_09_moderador_visualiza_botao_remover_post")

    clicar_botao_do_card(driver, card, "Remover post")

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert obter_status_post(post_id) == "removido"

    salvar_evidencia(driver, "test_09_moderador_removeu_post_interface")


def test_10_moderador_suspende_usuario_comum_pela_interface(driver):
    atualizar_status_usuario("bruno@trecho.com", "ativo", None, None)
    atualizar_status_usuario("alice@trecho.com", "ativo", None, None)

    conteudo = f"Post da Alice para suspensão pelo moderador {datetime.now().strftime('%H%M%S')}"

    preparar_post_com_denuncia_para_moderacao(
        conteudo=conteudo,
        autor_email="alice@trecho.com",
        denunciante_email="pedro@trecho.com",
        motivo="Denúncia para testar suspensão feita pelo moderador."
    )

    login(driver, "bruno@trecho.com")

    driver.get(f"{BASE_URL}/moderacao/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Painel de moderação")
    )

    card = encontrar_card_por_texto(driver, conteudo)

    assert "Suspender autor" in card.text

    salvar_evidencia(driver, "test_10_moderador_visualiza_botao_suspender_usuario")

    clicar_botao_do_card(driver, card, "Suspender autor")

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert obter_status_usuario("alice@trecho.com") == "suspenso"

    salvar_evidencia(driver, "test_10_moderador_suspendeu_usuario_interface")

    login(driver, "daniel@trecho.com")
    abrir_admin_e_validar_status(driver, "alice@trecho.com", "suspenso")

    atualizar_status_usuario("alice@trecho.com", "ativo", None, None)


def test_11_moderador_bane_usuario_comum_pela_interface(driver):
    atualizar_status_usuario("bruno@trecho.com", "ativo", None, None)
    atualizar_status_usuario("alice@trecho.com", "ativo", None, None)

    conteudo = f"Post da Alice para banimento pelo moderador {datetime.now().strftime('%H%M%S')}"

    preparar_post_com_denuncia_para_moderacao(
        conteudo=conteudo,
        autor_email="alice@trecho.com",
        denunciante_email="pedro@trecho.com",
        motivo="Denúncia para testar banimento feito pelo moderador."
    )

    login(driver, "bruno@trecho.com")

    driver.get(f"{BASE_URL}/moderacao/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Painel de moderação")
    )

    card = encontrar_card_por_texto(driver, conteudo)

    assert "Banir autor" in card.text

    salvar_evidencia(driver, "test_11_moderador_visualiza_botao_banir_usuario")

    clicar_botao_do_card(driver, card, "Banir autor")

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert obter_status_usuario("alice@trecho.com") == "banido"

    salvar_evidencia(driver, "test_11_moderador_baniu_usuario_interface")

    login(driver, "daniel@trecho.com")
    abrir_admin_e_validar_status(driver, "alice@trecho.com", "banido")

    atualizar_status_usuario("alice@trecho.com", "ativo", None, None)


def test_12_admin_suspende_moderador_pela_interface(driver):
    atualizar_status_usuario("daniel@trecho.com", "ativo", None, None)
    atualizar_status_usuario("bruno@trecho.com", "ativo", None, None)

    conteudo = f"Post do Bruno moderador para suspensão pelo admin {datetime.now().strftime('%H%M%S')}"

    preparar_post_com_denuncia_para_moderacao(
        conteudo=conteudo,
        autor_email="bruno@trecho.com",
        denunciante_email="pedro@trecho.com",
        motivo="Denúncia para testar suspensão de moderador pelo administrador."
    )

    login(driver, "daniel@trecho.com")

    driver.get(f"{BASE_URL}/moderacao/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Painel de moderação")
    )

    card = encontrar_card_por_texto(driver, conteudo)

    assert "Suspender autor" in card.text

    salvar_evidencia(driver, "test_12_admin_visualiza_botao_suspender_moderador")

    clicar_botao_do_card(driver, card, "Suspender autor")

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert obter_status_usuario("bruno@trecho.com") == "suspenso"

    salvar_evidencia(driver, "test_12_admin_suspendeu_moderador_interface")

    abrir_admin_e_validar_status(driver, "bruno@trecho.com", "suspenso")

    atualizar_status_usuario("bruno@trecho.com", "ativo", None, None)


def test_13_admin_bane_moderador_pela_interface(driver):
    atualizar_status_usuario("daniel@trecho.com", "ativo", None, None)
    atualizar_status_usuario("bruno@trecho.com", "ativo", None, None)

    conteudo = f"Post do Bruno moderador para banimento pelo admin {datetime.now().strftime('%H%M%S')}"

    preparar_post_com_denuncia_para_moderacao(
        conteudo=conteudo,
        autor_email="bruno@trecho.com",
        denunciante_email="pedro@trecho.com",
        motivo="Denúncia para testar banimento de moderador pelo administrador."
    )

    login(driver, "daniel@trecho.com")

    driver.get(f"{BASE_URL}/moderacao/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Painel de moderação")
    )

    card = encontrar_card_por_texto(driver, conteudo)

    assert "Banir autor" in card.text

    salvar_evidencia(driver, "test_13_admin_visualiza_botao_banir_moderador")

    clicar_botao_do_card(driver, card, "Banir autor")

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert obter_status_usuario("bruno@trecho.com") == "banido"

    salvar_evidencia(driver, "test_13_admin_baniu_moderador_interface")

    abrir_admin_e_validar_status(driver, "bruno@trecho.com", "banido")

    atualizar_status_usuario("bruno@trecho.com", "ativo", None, None)


def test_14_moderador_nao_pune_administrador(driver):
    atualizar_status_usuario("bruno@trecho.com", "ativo", None, None)
    atualizar_status_usuario("daniel@trecho.com", "ativo", None, None)

    conteudo = f"Post do administrador para testar hierarquia {datetime.now().strftime('%H%M%S')}"

    preparar_post_com_denuncia_para_moderacao(
        conteudo=conteudo,
        autor_email="daniel@trecho.com",
        denunciante_email="pedro@trecho.com",
        motivo="Denúncia usada para testar hierarquia entre moderador e administrador."
    )

    login(driver, "bruno@trecho.com")

    driver.get(f"{BASE_URL}/moderacao/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Painel de moderação")
    )

    assert "Moderadores não podem" in driver.page_source or "administradores" in driver.page_source

    salvar_evidencia(driver, "test_14_moderador_nao_pune_administrador")


def test_15_admin_acessa_administracao(driver):
    atualizar_status_usuario("daniel@trecho.com", "ativo", None, None)

    login(driver, "daniel@trecho.com")

    driver.get(f"{BASE_URL}/admin/")
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert "Administração" in driver.page_source

    salvar_evidencia(driver, "test_15_admin_acessou_administracao")


def test_16_admin_acessa_relatorios(driver):
    atualizar_status_usuario("daniel@trecho.com", "ativo", None, None)

    login(driver, "daniel@trecho.com")

    driver.get(f"{BASE_URL}/relatorios/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Relatórios")
    )

    assert "Histórico de moderação" in driver.page_source
    assert "Ranking de posts por engajamento" in driver.page_source

    salvar_evidencia(driver, "test_16_admin_acessou_relatorios")


def test_17_usuario_suspenso_consegue_logar_mas_nao_postar(driver):
    atualizar_status_usuario(
        "alice@trecho.com",
        "suspenso",
        datetime.now() + timedelta(days=1),
        "Suspensão aplicada para validar bloqueio de postagem."
    )

    login(driver, "alice@trecho.com", fechar_modal=False)

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    pausar()

    assert "Conta suspensa" in driver.page_source or "suspensa" in driver.page_source

    salvar_evidencia(driver, "test_17_usuario_suspenso_modal")

    fechar_modais(driver)

    conteudo = f"Tentativa de post suspenso {datetime.now().strftime('%H%M%S')}"

    preencher_e_enviar_post(driver, conteudo)

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert conteudo not in driver.page_source
    assert "suspensa" in driver.page_source or "suspenso" in driver.page_source

    salvar_evidencia(driver, "test_17_usuario_suspenso_nao_consegue_postar")

    atualizar_status_usuario("alice@trecho.com", "ativo", None, None)


def test_18_usuario_banido_nao_consegue_logar(driver):
    atualizar_status_usuario(
        "alice@trecho.com",
        "banido",
        None,
        "Banimento aplicado para validar bloqueio de login."
    )

    driver.get(f"{BASE_URL}/auth/logout")
    pausar()

    driver.get(f"{BASE_URL}/auth/login")
    pausar()

    campo_email = esperar(driver).until(
        EC.presence_of_element_located((By.NAME, "email"))
    )
    campo_email.clear()
    campo_email.send_keys("alice@trecho.com")
    pausar()

    campo_senha = driver.find_element(By.NAME, "senha")
    campo_senha.clear()
    campo_senha.send_keys("123456")
    pausar()

    salvar_evidencia(driver, "test_18_usuario_banido_login_preenchido")

    botao_login = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    botao_login.click()
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert "Conta banida" in driver.page_source or "banida" in driver.page_source

    salvar_evidencia(driver, "test_18_usuario_banido_bloqueado")

    atualizar_status_usuario("alice@trecho.com", "ativo", None, None)


def test_19_admin_visualiza_logs_e_usuarios(driver):
    atualizar_status_usuario("daniel@trecho.com", "ativo", None, None)

    login(driver, "daniel@trecho.com")

    driver.get(f"{BASE_URL}/admin/")
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert "Usuários cadastrados" in driver.page_source or "Últimos logins" in driver.page_source

    salvar_evidencia(driver, "test_19_admin_visualiza_usuarios_e_logs")


def test_20_relatorios_mostram_engajamento_denuncias_e_moderacao(driver):
    atualizar_status_usuario("carla@trecho.com", "ativo", None, None)

    login(driver, "carla@trecho.com")

    driver.get(f"{BASE_URL}/relatorios/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Relatórios")
    )

    assert "Ranking de posts por engajamento" in driver.page_source
    assert "Usuários por perfil" in driver.page_source
    assert "Denúncias por status" in driver.page_source

    salvar_evidencia(driver, "test_20_relatorios_engajamento_denuncias_moderacao")
