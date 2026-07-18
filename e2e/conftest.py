"""Fixtures para a suíte E2E.

Testes aqui não usam o test client do Django nem o banco diretamente — eles
dirigem um navegador real contra o frontend buildado e o backend rodando de
verdade (ver .github/workflows/ci.yml, job e2e). Por isso vivem fora de
backend/apps/*/tests: são uma suíte de outra natureza, com outro runtime e
outras dependências (Selenium), não testes unitários de Django.
"""
import os
import uuid

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("E2E_BASE_URL", "http://localhost:4173")


@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    browser = webdriver.Chrome(options=options)
    browser.implicitly_wait(5)
    try:
        yield browser
    finally:
        browser.quit()


@pytest.fixture
def unique_email() -> str:
    return f"e2e-{uuid.uuid4().hex[:12]}@example.com"
