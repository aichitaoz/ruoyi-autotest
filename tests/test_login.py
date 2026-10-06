"""登录测试"""
from pages.login_page import LoginPage
from config import BASE_URL, USERNAME, PASSWORD


def test_login_success(driver):
    """测试登录成功"""
    login_page = LoginPage(driver)
    login_page.open(BASE_URL)
    login_page.login(USERNAME, PASSWORD)
    login_page.wait_for_home()

    assert "/index" in login_page.current_url()