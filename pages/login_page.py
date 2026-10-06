"""登录页面"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage
from config import TIMEOUT


class LoginPage(BasePage):
    # 元素定位器集中在这里，页面一改只改这几行
    USERNAME_INPUT = (By.CSS_SELECTOR, "input[placeholder='账号']")
    PASSWORD_INPUT = (By.CSS_SELECTOR, "input[placeholder='密码']")
    LOGIN_BUTTON   = (By.CSS_SELECTOR, "button.el-button--primary")

    def login(self, username, password):
        """执行登录"""
        self.input_text(self.USERNAME_INPUT, username)
        self.input_text(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)

    def wait_for_home(self):
        """等待跳转到首页"""
        WebDriverWait(self.driver, TIMEOUT).until(
            EC.url_contains("/index")
        )