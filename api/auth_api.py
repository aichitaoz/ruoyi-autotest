"""认证相关接口封装"""
import requests
from config import API_BASE_URL


class AuthApi:
    """认证接口"""

    @staticmethod
    def login(username, password):
        """登录，返回响应对象"""
        return requests.post(
            f"{API_BASE_URL}/login",
            json={"username": username, "password": password},
        )
