import os
import time
from datetime import datetime
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


@pytest.fixture(scope="session", autouse=True)
def preparar_banco_para_testes():
    app = create_app()

    with app.app_context():
        emails_teste = [
            "pedro@trecho.com",
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

        if pedro:
            total_posts = db.session.execute(
                text("""
                    SELECT COUNT(*) AS total
                    FROM posts
                    WHERE status_post = 'ativo'
                """)
            ).scalar()

            if total_posts == 0:
                db.session.execute(
                    text("""
                        INSERT INTO posts (usuario_id, conteudo)
                        VALUES (:usuario_id, :conteudo)
                    """),
                    {
                        "usuario_id": pedro.id,
                        "conteudo": "Post inicial criado automaticamente para os testes Selenium."
                    }
                )
                db.session.commit()


@pytest.fixture(scope="session")
def driver():
    EVIDENCIAS_DIR.mkdir(exist_ok=True)

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=1366,900")
        driver = webdriver.Chrome(options=options)
    except WebDriverException:
        options = webdriver.FirefoxOptions()
        options.add_argument("--width=1366")
        options.add_argument("--height=900")
        driver = webdriver.Firefox(options=options)

    time.sleep(1)

    yield driver

    time.sleep(1)
    driver.quit()


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


def logout(driver):
    driver.get(f"{BASE_URL}/auth/logout")
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    fechar_modais(driver)


def login(driver, email, senha="123456"):
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

    botao_login = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    botao_login.click()
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    fechar_modais(driver)

    assert "E-mail ou senha inválidos" not in driver.page_source
    assert "Esta conta não está ativa" not in driver.page_source


def test_01_feed_publico_abre(driver):
    driver.get(BASE_URL)
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    fechar_modais(driver)

    assert "Trecho" in driver.page_source

    salvar_evidencia(driver, "test_01_feed_publico_abre")


def test_02_usuario_comum_cria_post(driver):
    login(driver, "pedro@trecho.com")

    campo = esperar(driver).until(
        EC.presence_of_element_located((By.ID, "campoPostFeed"))
    )
    pausar()

    conteudo = f"Post criado pelo teste Selenium {datetime.now().strftime('%H%M%S')}"
    campo.clear()
    campo.send_keys(conteudo)
    pausar()

    driver.execute_script("""
        const campo = document.getElementById('campoPostFeed');
        const botao = document.getElementById('botaoPostarFeed');

        campo.dispatchEvent(new Event('input', { bubbles: true }));
        botao.disabled = false;
    """)
    pausar()

    fechar_modais(driver)

    botao = driver.find_element(By.ID, "botaoPostarFeed")

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
    pausar()

    driver.execute_script("arguments[0].click();", botao)
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Post publicado com sucesso")
    )

    assert conteudo in driver.page_source

    salvar_evidencia(driver, "test_02_usuario_comum_cria_post")


def test_03_usuario_curte_post(driver):
    login(driver, "pedro@trecho.com")

    fechar_modais(driver)

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

    salvar_evidencia(driver, "test_03_usuario_curte_post")


def test_04_analista_acessa_relatorios_e_nao_posta(driver):
    login(driver, "carla@trecho.com")

    pausar()

    assert "Novo post" not in driver.page_source

    campos_postagem = driver.find_elements(By.ID, "campoPostFeed")
    assert len(campos_postagem) == 0

    driver.get(f"{BASE_URL}/relatorios/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Relatórios")
    )

    assert "Ranking de posts por engajamento" in driver.page_source
    assert "Usuários por perfil" in driver.page_source
    assert "Denúncias por status" in driver.page_source

    salvar_evidencia(driver, "test_04_analista_acessa_relatorios_e_nao_posta")


def test_05_moderador_acessa_moderacao(driver):
    login(driver, "bruno@trecho.com")

    driver.get(f"{BASE_URL}/moderacao/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Painel de moderação")
    )

    assert "Painel de moderação" in driver.page_source

    salvar_evidencia(driver, "test_05_moderador_acessa_moderacao")


def test_06_admin_acessa_administracao_e_relatorios(driver):
    login(driver, "daniel@trecho.com")

    driver.get(f"{BASE_URL}/admin/")
    pausar()

    esperar(driver).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    assert "Administração" in driver.page_source

    driver.get(f"{BASE_URL}/relatorios/")
    pausar()

    esperar(driver).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Relatórios")
    )

    assert "Histórico de moderação" in driver.page_source

    salvar_evidencia(driver, "test_06_admin_acessa_administracao_e_relatorios")