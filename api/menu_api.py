"""菜单管理相关接口封装"""
import requests
from config import API_BASE_URL


class MenuApi:
    """菜单管理接口。

    菜单模块探路确认的几个特点（都和部门模块不一样，别照抄部门的写法）：
    1. 列表返回 {msg, code, data}，但 data 是**平铺的一维数组**（不是部门那种嵌套树），
       每条都带一个空的 children 字段，不用递归就能遍历
    2. 菜单**没有 del_flag 列**，删除是**物理删除**，删完库里就没了，按 id 单查也不会再有 data
    3. 必填字段只有三个：menuName / menuType / orderNum。
       path、component、perms 全都不是必填 —— 目录（M）不给 path 能建成功，
       菜单（C）不给 component / perms 也能建成功，按钮（F）不给 perms 照样能建
    4. menuName 是**全局唯一**（不分父级），perms **不唯一**（可以重复）
    5. parentId 传0 能建根菜单，传不存在的 id（如 99999）也**不报错**，直接建成功
    6. 删除只有一条约束：有子菜单时返回 code=601；
       **没有**「被角色引用不允许删除」这类校验
    """

    # 三种菜单类型
    TYPE_DIR = "M"     # 目录
    TYPE_MENU = "C"    # 菜单
    TYPE_BUTTON = "F"  # 按钮

    @staticmethod
    def get_list(token, menu_name=None, status=None):
        """查询菜单列表（平铺），返回响应对象。
        这个接口不分页，一次返回全部菜单（103+ 条），pageSize 传了也不生效。
        menu_name / status 是可选过滤条件。"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {}
        if menu_name is not None:
            params["menuName"] = menu_name
        if status is not None:
            params["status"] = status
        return requests.get(
            f"{API_BASE_URL}/system/menu/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def get_by_id(token, menu_id):
        """按 id 查询单个菜单，返回响应对象。
        查不存在的 id 返回 code=200 且无 data 字段（菜单是物理删除）"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(f"{API_BASE_URL}/system/menu/{menu_id}", headers=headers)

    @staticmethod
    def add(token, parent_id, menu_name, menu_type, order_num=1,
            path=None, component=None, perms=None, status="0",
            visible="0", icon=None, query=None):
        """新增菜单，返回响应对象。

        只有 menu_name / menu_type / order_num 是必填（缺了分别报
        「菜单名称不能为空」「菜单类型不能为空」「显示顺序不能为空」）。
        path / component / perms 都不是必填，按类型给就行：
        - M 目录：一般给 path
        - C 菜单：给 path + component，可选 perms
        - F 按钮：给perms 即可，path / component 不用管

        注意 menu_name 全局唯一，重复会报「菜单名称已存在」；
        perms 可以重复；parent_id 传 0 建根菜单、传不存在的 id 也不报错。"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "parentId": parent_id,
            "menuName": menu_name,
            "menuType": menu_type,
            "orderNum": order_num,
            "status": status,
            "visible": visible,
        }
        # 可选字段：只传非空的，避免给 null 值干扰后端默认值
        if path is not None:
            payload["path"] = path
        if component is not None:
            payload["component"] = component
        if perms is not None:
            payload["perms"] = perms
        if icon is not None:
            payload["icon"] = icon
        if query is not None:
            payload["query"] = query
        return requests.post(
            f"{API_BASE_URL}/system/menu",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def update(token, menu_id, parent_id, menu_name, menu_type, order_num=1,
               path=None, component=None, perms=None, status="0",
               visible="0", icon=None, query=None):
        """修改菜单，返回响应对象。menu_id 必填，其余字段按 add 的规则传。"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "menuId": menu_id,
            "parentId": parent_id,
            "menuName": menu_name,
            "menuType": menu_type,
            "orderNum": order_num,
            "status": status,
            "visible": visible,
        }
        if path is not None:
            payload["path"] = path
        if component is not None:
            payload["component"] = component
        if perms is not None:
            payload["perms"] = perms
        if icon is not None:
            payload["icon"] = icon
        if query is not None:
            payload["query"] = query
        return requests.put(
            f"{API_BASE_URL}/system/menu",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def delete(token, menu_id):
        """删除菜单，返回响应对象。注意菜单删除是**物理删除**
        （sys_menu 表没有 del_flag 列），删后列表查不到，按 id 单查也不会再有 data。

        唯一约束：存在子菜单时返回 code=601「存在子菜单,不允许删除」（逗号是半角）。
        菜单没有「被角色引用不允许删除」这类校验，删不存在的 id 也会返回 601。"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.delete(
            f"{API_BASE_URL}/system/menu/{menu_id}",
            headers=headers,
        )