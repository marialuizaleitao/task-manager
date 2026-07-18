from support import click_button, fill_labeled_input, wait_for_text

PASSWORD = "SenhaForte123"


class TestRegistrationAndLogin:
    def test_register_logout_and_login(self, driver, base_url, unique_email):
        driver.get(f"{base_url}/register")

        fill_labeled_input(driver, "Nome", "Maria")
        fill_labeled_input(driver, "Sobrenome", "Teste")
        fill_labeled_input(driver, "E-mail", unique_email)
        fill_labeled_input(driver, "Senha", PASSWORD)
        fill_labeled_input(driver, "Confirmar senha", PASSWORD)
        click_button(driver, "Criar conta")

        wait_for_text(driver, "Bem-vindo")

        click_button(driver, "Sair")
        wait_for_text(driver, "Entrar")

        fill_labeled_input(driver, "E-mail", unique_email)
        fill_labeled_input(driver, "Senha", PASSWORD)
        click_button(driver, "Entrar")

        wait_for_text(driver, "Bem-vindo")

    def test_login_with_wrong_password_shows_error(self, driver, base_url, unique_email):
        driver.get(f"{base_url}/register")
        fill_labeled_input(driver, "Nome", "Maria")
        fill_labeled_input(driver, "Sobrenome", "Teste")
        fill_labeled_input(driver, "E-mail", unique_email)
        fill_labeled_input(driver, "Senha", PASSWORD)
        fill_labeled_input(driver, "Confirmar senha", PASSWORD)
        click_button(driver, "Criar conta")
        wait_for_text(driver, "Bem-vindo")

        click_button(driver, "Sair")
        wait_for_text(driver, "Entrar")

        fill_labeled_input(driver, "E-mail", unique_email)
        fill_labeled_input(driver, "Senha", "senha-errada")
        click_button(driver, "Entrar")

        wait_for_text(driver, "E-mail ou senha inválidos")
