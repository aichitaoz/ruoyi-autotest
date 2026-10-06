"""用户管理页面"""
from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from config import BASE_URL


class UserPage(BasePage):
    # ---------- 新增弹窗 ----------
    ADD_BUTTON     = (By.XPATH, "//button[contains(., '新增')]")
    NICKNAME_INPUT = (By.CSS_SELECTOR, ".el-dialog input[placeholder='请输入用户昵称']")
    USERNAME_INPUT = (By.CSS_SELECTOR, ".el-dialog input[placeholder='请输入用户名称']")
    PASSWORD_INPUT = (By.CSS_SELECTOR, ".el-dialog input[placeholder='请输入用户密码']")
    SUBMIT_BUTTON  = (By.XPATH, "//div[contains(@class,'el-dialog')][.//span[contains(text(),'添加用户')]]//button[contains(@class,'el-button--primary')]")

    # ---------- 搜索区 ----------
    SEARCH_USERNAME = (By.CSS_SELECTOR, ".el-form input[placeholder='请输入用户名称']")
    SEARCH_BUTTON   = (By.XPATH, "//button[.//span[normalize-space()='搜索']]")

    # ---------- 列表区 ----------
    TABLE_ROWS = (By.CSS_SELECTOR, ".el-table__row")

    # ---------- 删除功能 ----------
    DELETE_BUTTON_IN_ROW = (By.XPATH, ".//button[.//span[text()='删除']]")
    CONFIRM_DELETE_BUTTON = (By.XPATH, "//div[contains(@class,'el-message-box')]//button[contains(@class,'el-button--primary')]")

    def open(self):
        """打开用户管理页面"""
        self.driver.get(f"{BASE_URL}/system/user")

    def click_add(self):
        """点新增"""
        self.click(self.ADD_BUTTON)

    def fill_form(self, nickname, username, password):
        """填弹窗表单"""
        self.input_text(self.NICKNAME_INPUT, nickname)
        self.input_text(self.USERNAME_INPUT, username)
        self.input_text(self.PASSWORD_INPUT, password)

    def submit(self):
        """点确定"""
        self.click(self.SUBMIT_BUTTON)

    def search(self, keyword):
        """按用户名搜索"""
        self.input_text(self.SEARCH_USERNAME, keyword)
        self.click(self.SEARCH_BUTTON)

    def has_user_in_list(self, username):
        """判断列表里有没有某用户"""
        rows = self.driver.find_elements(*self.TABLE_ROWS)
        for row in rows:
            if username in row.text:
                return True
        return False
    def delete_user(self, username):
        """删除指定用户名的用户（先搜索，再点删除，最后确认）"""
        # 1. 搜索
        self.search(username)
        import time
        time.sleep(1)

        # 2. 找到该用户所在行的删除按钮
        rows = self.driver.find_elements(*self.TABLE_ROWS)
        for row in rows:
            if username in row.text:
                delete_btn = row.find_element(*self.DELETE_BUTTON_IN_ROW)
                delete_btn.click()
                time.sleep(1)
                # 3. 点二次确认的"确定"
                self.click(self.CONFIRM_DELETE_BUTTON)
                time.sleep(1)
                return True
        return False

    def delete_if_exists(self, username):
        """如果用户存在就删除，不存在就跳过（用于测试前清理）"""
        exists = self.has_user_in_list(username)
        print(f"[clean] {username} 是否存在: {exists}")
        if exists:
            result = self.delete_user(username)
            print(f"[clean] {username} 删除结果: {result}")
            return result
        return False