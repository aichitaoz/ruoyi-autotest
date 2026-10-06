"""UI 测试的共享 fixture"""
import pymysql
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    BASE_URL, USERNAME, PASSWORD,
    HEADLESS, WINDOW_WIDTH, WINDOW_HEIGHT,
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME,
)
from pages.login_page import LoginPage


def cleanup_test_users():
    """用 SQL 清掉所有测试用户（用户名以 autotest 开头）"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM sys_user WHERE user_name LIKE 'autotest%%'"
            )
            deleted = cursor.rowcount
        conn.commit()
        print(f"[clean] 已清理 {deleted} 个测试用户")
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_once_before_session():
    """整个测试会话开始前，清一次 autotest 用户"""
    cleanup_test_users()


@pytest.fixture(scope="function")
def driver():
    """每个测试启动一次浏览器"""
    options = Options()

    if HEADLESS:
        options.add_argument("--headless=new")

    options.add_argument(f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    yield driver
    driver.quit()


@pytest.fixture(scope="function")
def logged_in_driver(driver):
    """已登录的浏览器"""
    login_page = LoginPage(driver)
    login_page.open(BASE_URL)
    login_page.login(USERNAME, PASSWORD)
    login_page.wait_for_home()
    return driver


@pytest.fixture(scope="function")
def clean_driver(logged_in_driver):
    """登录后的 driver（清理已移到 session 级）"""
    yield logged_in_driver