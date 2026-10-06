"""接口测试：登录"""
import requests
from api.auth_api import AuthApi
from config import API_BASE_URL


def test_login_success():
    """正确的账号密码，能拿到 token"""
    r = AuthApi.login("admin", "admin123")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "token" in body
    assert len(body["token"]) > 0


def test_login_wrong_password():
    """密码错误，登录应该失败"""
    r = AuthApi.login("admin", "wrong_password_123")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 500
    assert body["msg"] == "用户不存在/密码错误"
    assert "token" not in body


def test_getinfo_without_token():
    """不带 token 访问 /getInfo，应该被拒绝"""
    r = requests.get(f"{API_BASE_URL}/getInfo")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 401
    assert "认证失败" in body["msg"]


def test_getinfo_with_invalid_token():
    """带一个伪造的 token 访问 /getInfo，应该被拒绝"""
    headers = {"Authorization": "Bearer fake_token_123456"}
    r = requests.get(f"{API_BASE_URL}/getInfo", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 401
    assert "认证失败" in body["msg"]


def test_getinfo_with_wrong_scheme():
    """token 前不写 Bearer 前缀，应该被拒绝"""
    headers = {"Authorization": "fake_token_123456"}
    r = requests.get(f"{API_BASE_URL}/getInfo", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 401


def test_getinfo_with_valid_token(token):
    """带正确 token 访问 /getInfo，应该成功"""
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE_URL}/getInfo", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["user"]["userName"] == "admin"
    assert "admin" in body["roles"]