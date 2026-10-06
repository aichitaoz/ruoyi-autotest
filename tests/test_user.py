"""用户管理测试——数据驱动 + 多级断言"""
import csv
import time
import os
import pytest
from pages.user_page import UserPage
from config import USERS_CSV


def read_csv(path):
    """读取 CSV，返回字典列表"""
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("data", read_csv(USERS_CSV))
def test_add_user(clean_driver, data):
    """数据驱动：新增用户 + 三层断言"""
    user_page = UserPage(clean_driver)
    user_page.open()
    time.sleep(2)

    # 1. 新增用户
    user_page.click_add()
    time.sleep(2)
    user_page.fill_form(data["nickname"], data["username"], data["password"])
    user_page.submit()

    # 2. 第一层断言：提示出现
    user_page.wait_text(data["expected"])
    assert user_page.is_text_present(data["expected"]), \
        f"没有出现提示：{data['expected']}"

    # 3. 第二层断言：列表里能搜到
    time.sleep(1)
    user_page.search(data["username"])
    time.sleep(1)
    assert user_page.has_user_in_list(data["username"]), \
        f"新增后列表里找不到用户：{data['username']}"

