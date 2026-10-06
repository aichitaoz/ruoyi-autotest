"""用户管理相关接口封装"""
import requests
from config import API_BASE_URL


class UserApi:
    """用户管理接口"""

    @staticmethod
    def get_list(token, page_size=100):
        """查询用户列表，返回响应对象。page_size 默认 100，避免分页漏数据。"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {"pageNum": 1, "pageSize": page_size}
        return requests.get(
            f"{API_BASE_URL}/system/user/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def get_by_id(token, user_id):
        """按 id 查询单个用户，返回响应对象"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(f"{API_BASE_URL}/system/user/{user_id}", headers=headers)

    @staticmethod
    def add(token, username, nickname, password):
        """新增用户，返回响应对象"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "userName": username,
            "nickName": nickname,
            "password": password,
        }
        return requests.post(
            f"{API_BASE_URL}/system/user",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def update(token, user_id, username, nickname):
        """修改用户，返回响应对象"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "userId": user_id,
            "userName": username,
            "nickName": nickname,
        }
        return requests.put(
            f"{API_BASE_URL}/system/user",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def delete(token, user_id):
        """删除用户，返回响应对象。注意 RuoYi 是软删除，删后列表里查不到，但按 id 单查仍可查到"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.delete(
            f"{API_BASE_URL}/system/user/{user_id}",
            headers=headers,
        )