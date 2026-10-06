"""角色管理相关接口封装"""
import requests
from config import API_BASE_URL


class RoleApi:
    """角色管理接口"""

    @staticmethod
    def get_list(token, page_size=100):
        """查询角色列表，返回响应对象。page_size 默认 100，避免分页漏数据"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {"pageNum": 1, "pageSize": page_size}
        return requests.get(
            f"{API_BASE_URL}/system/role/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def get_by_id(token, role_id):
        """按 id 查询单个角色，返回响应对象"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(f"{API_BASE_URL}/system/role/{role_id}", headers=headers)

    @staticmethod
    def add(token, role_name, role_key, role_sort=1, status="0", menu_ids=None):
        """新增角色，返回响应对象。role_name / role_key 必填，权限字符重复会被拒"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "roleName": role_name,
            "roleKey": role_key,
            "roleSort": role_sort,
            "status": status,
            "menuIds": menu_ids if menu_ids is not None else [],
        }
        return requests.post(
            f"{API_BASE_URL}/system/role",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def update(token, role_id, role_name, role_key, role_sort=1, status="0", menu_ids=None):
        """修改角色，返回响应对象。role_id 必填"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "roleId": role_id,
            "roleName": role_name,
            "roleKey": role_key,
            "roleSort": role_sort,
            "status": status,
            "menuIds": menu_ids if menu_ids is not None else [],
        }
        return requests.put(
            f"{API_BASE_URL}/system/role",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def delete(token, role_id):
        """删除角色，返回响应对象。注意 RuoYi 是软删除，删后列表里查不到，但按 id 单查仍能查到"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.delete(
            f"{API_BASE_URL}/system/role/{role_id}",
            headers=headers,
        )