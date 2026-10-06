"""岗位管理相关接口封装"""
import requests
from config import API_BASE_URL


class PostApi:
    """岗位管理接口"""

    @staticmethod
    def get_list(token, page_size=100):
        """查询岗位列表，返回响应对象。page_size 默认 100，避免分页漏数据"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {"pageNum": 1, "pageSize": page_size}
        return requests.get(
            f"{API_BASE_URL}/system/post/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def get_by_id(token, post_id):
        """按 id 查询单个岗位，返回响应对象。注意查不存在的 id 也返回 code=200，但 data 为空"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(f"{API_BASE_URL}/system/post/{post_id}", headers=headers)

    @staticmethod
    def add(token, post_code, post_name, post_sort=1, status="0"):
        """新增岗位，返回响应对象。
        post_code / post_name / post_sort 都必填，缺一个报对应中文提示；
        status 在库里是 NOT NULL 且无默认值，漏传会直接抛 SQL 异常，所以这里默认带上"0"（正常）"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "postCode": post_code,
            "postName": post_name,
            "postSort": post_sort,
            "status": status,
        }
        return requests.post(
            f"{API_BASE_URL}/system/post",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def update(token, post_id, post_code, post_name, post_sort=1, status="0"):
        """修改岗位，返回响应对象。post_id 必填"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "postId": post_id,
            "postCode": post_code,
            "postName": post_name,
            "postSort": post_sort,
            "status": status,
        }
        return requests.put(
            f"{API_BASE_URL}/system/post",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def delete(token, post_id):
        """删除岗位，返回响应对象。注意岗位删除是物理删除（sys_post 表没有 del_flag 列），
        删完按 id 单查只会返回 code=200 且无 data 字段"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.delete(
            f"{API_BASE_URL}/system/post/{post_id}",
            headers=headers,
        )