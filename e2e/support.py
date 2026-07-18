"""Helpers de interação usados pelos testes E2E.

O frontend não expõe atributos data-testid (fora do escopo desta sprint —
seria uma mudança no frontend, não apenas em testes). Os seletores aqui se
apoiam na associação label/input já existente em todo formulário do projeto
(<label>Texto<input /></label>), que é estável desde a Sprint 0.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


def fill_labeled_input(driver, label_text: str, value: str) -> None:
    field = driver.find_element(By.XPATH, f"//label[contains(., '{label_text}')]/input")
    field.clear()
    field.send_keys(value)


def select_labeled_option(driver, label_text: str, option_text: str) -> None:
    field = driver.find_element(By.XPATH, f"//label[contains(., '{label_text}')]/select")
    Select(field).select_by_visible_text(option_text)


def click_button(driver, text: str) -> None:
    driver.find_element(By.XPATH, f"//button[normalize-space(text())='{text}']").click()


def wait_for_text(driver, text: str, timeout: int = 10) -> None:
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{text}')]"))
    )


def wait_for_class(driver, xpath: str, class_name: str, timeout: int = 10) -> None:
    """Aguarda até que o elemento localizado por xpath tenha class_name.

    Relocaliza o elemento a cada tentativa, em vez de reutilizar uma
    referência já capturada: o React pode remontar o nó ao reagir à mudança
    de estado, o que tornaria uma referência antiga inválida (stale).
    """
    WebDriverWait(driver, timeout).until(
        lambda d: class_name in d.find_element(By.XPATH, xpath).get_attribute("class")
    )
