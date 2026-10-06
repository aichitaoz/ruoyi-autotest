"""基础页面类：封装所有页面通用的操作"""
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import TIMEOUT


class BasePage:
    def __init__(self, driver):
        self.driver = driver

    def open(self, url):
        """打开网址"""
        self.driver.get(url)

    def find(self, locator, timeout=TIMEOUT):
        """等待元素出现并返回"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )

    def click(self, locator, timeout=TIMEOUT):
        """等待元素可点击并点击"""
        elem = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        elem.click()

    def input_text(self, locator, text, timeout=TIMEOUT):
        """清空后输入文本"""
        elem = self.find(locator, timeout)
        elem.clear()
        elem.send_keys(text)

    def wait_text(self, text, timeout=TIMEOUT):
        """等待页面上出现某段文字"""
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(("xpath", f"//*[contains(text(), '{text}')]"))
        )

    def is_text_present(self, text):
        """判断页面源码里有没有某段文字（不等待）"""
        return text in self.driver.page_source

    def current_url(self):
        return self.driver.current_url