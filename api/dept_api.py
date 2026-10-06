"""部门管理相关接口封装"""
import requests
from config import API_BASE_URL


class DeptApi:
    """部门管理接口。

    注意部门模块和其他模块三个不一样的地方（都已实测确认）：
    1. 列表返回的是 {msg, code, data}，data 是**树形嵌套结构**，没有 total / rows
    2. 列表**不支持分页**，pageNum / pageSize 传了也不生效，永远返回全量树
    3. 删除部门是**软删除**（sys_dept 有 del_flag 列），删后列表查不到，但按 id 单查仍能查到
    """

    @staticmethod
    def get_list(token, dept_name=None, status=None):
        """查询部门列表（树形），返回响应对象。
        dept_name 按名称模糊过滤，status 按状态过滤；
        传了分页参数也没用，这个接口不分页，历史数据全靠 name/status 过滤。"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {}
        if dept_name is not None:
            params["deptName"] = dept_name
        if status is not None:
            params["status"] = status
        return requests.get(
            f"{API_BASE_URL}/system/dept/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def get_by_id(token, dept_id):
        """按 id 查询单个部门，返回响应对象。注意查不存在的 id 也返回 code=200 但无 data 字段"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(f"{API_BASE_URL}/system/dept/{dept_id}", headers=headers)

    @staticmethod
    def add(token, parent_id, dept_name, order_num=1, status="0"):
        """新增部门，返回响应对象。
        parent_id 必须是**真实存在**的部门 id，传空 / 0 / 不存在的 id 都会返回 code=500 且 msg 为 null
        （RuoYi 不允许通过接口建根部门）；
        dept_name 在**同一个父部门下**唯一，不同父部门下可以同名；
        order_num 必填，漏传报「显示顺序不能为空」"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "parentId": parent_id,
            "deptName": dept_name,
            "orderNum": order_num,
            "status": status,
        }
        return requests.post(
            f"{API_BASE_URL}/system/dept",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def update(token, dept_id, parent_id, dept_name, order_num=1, status="0"):
        """修改部门，返回响应对象。dept_id / parent_id 必填"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "deptId": dept_id,
            "parentId": parent_id,
            "deptName": dept_name,
            "orderNum": order_num,
            "status": status,
        }
        return requests.put(
            f"{API_BASE_URL}/system/dept",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def delete(token, dept_id):
        """删除部门，返回响应对象。注意部门删除是软删除（sys_dept 表有 del_flag 列），
        删后列表里查不到，但按 id 单查仍能查到。
        删除有两条约束，被拒时返回 code=601（注意 msg 里的逗号是半角英文逗号）：
        - 存在下级部门 ->「存在下级部门,不允许删除」
        - 部门存在用户 ->「部门存在用户,不允许删除」"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.delete(
            f"{API_BASE_URL}/system/dept/{dept_id}",
            headers=headers,
        )