from selenium.webdriver.common.by import By

from support import click_button, fill_labeled_input, wait_for_class, wait_for_text

PASSWORD = "SenhaForte123"


def _register_and_login(driver, base_url, email: str) -> None:
    driver.get(f"{base_url}/register")
    fill_labeled_input(driver, "Nome", "Maria")
    fill_labeled_input(driver, "Sobrenome", "Teste")
    fill_labeled_input(driver, "E-mail", email)
    fill_labeled_input(driver, "Senha", PASSWORD)
    fill_labeled_input(driver, "Confirmar senha", PASSWORD)
    click_button(driver, "Criar conta")
    wait_for_text(driver, "Bem-vindo")


class TestTaskLifecycle:
    def test_create_complete_and_delete_task(self, driver, base_url, unique_email):
        _register_and_login(driver, base_url, unique_email)

        driver.get(f"{base_url}/tasks")
        wait_for_text(driver, "Nenhuma tarefa cadastrada")

        fill_labeled_input(driver, "Título", "Preparar apresentação")
        click_button(driver, "Criar tarefa")
        wait_for_text(driver, "Preparar apresentação")

        item_xpath = "//strong[text()='Preparar apresentação']/ancestor::li"
        task_item = driver.find_element(By.XPATH, item_xpath)
        task_item.find_element(By.XPATH, ".//input[@type='checkbox']").click()

        wait_for_class(driver, item_xpath, "task-item--completed")
        task_item = driver.find_element(By.XPATH, item_xpath)
        assert "task-item--completed" in task_item.get_attribute("class")

        task_item.find_element(By.XPATH, ".//button[text()='Excluir']").click()
        driver.switch_to.alert.accept()

        wait_for_text(driver, "Nenhuma tarefa cadastrada")
        assert not driver.find_elements(By.XPATH, "//strong[text()='Preparar apresentação']")

    def test_edit_task_updates_title(self, driver, base_url, unique_email):
        _register_and_login(driver, base_url, unique_email)

        driver.get(f"{base_url}/tasks")
        wait_for_text(driver, "Nenhuma tarefa cadastrada")

        fill_labeled_input(driver, "Título", "Rascunho")
        click_button(driver, "Criar tarefa")
        wait_for_text(driver, "Rascunho")

        task_item = driver.find_element(By.XPATH, "//strong[text()='Rascunho']/ancestor::li")
        task_item.find_element(By.XPATH, ".//button[text()='Editar']").click()

        fill_labeled_input(driver, "Título", "Relatório final")
        click_button(driver, "Salvar")

        wait_for_text(driver, "Relatório final")
        assert not driver.find_elements(By.XPATH, "//strong[text()='Rascunho']")
