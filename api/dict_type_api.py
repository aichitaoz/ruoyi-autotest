"""字典类型相关接口封装"""
import requests
from config import API_BASE_URL


class DictTypeApi:
    """字典类型接口。

    探路确认的几个特点：
    1. 列表是标准的 {total, rows, code, msg}，**分页有效**（pageSize / pageNum 都生效）
    2. sys_dict_type **没有 del_flag 列**，删除是**物理删除**，删完按 id 单查也不会再有 data
    3. dict_type 唯一（DB 层还有唯一索引 dict_type），重复报「字典类型已存在」；
       dictName **不唯一**，可以重名
    4. 必填只有dictName / dictType 两个，status 不传也能建（后端默认给 "0"）
    5. dictType 还有**格式校验**：必须字母开头，且只能是（小写字母，数字，下划线），
       不符合报「字典类型必须以字母开头，且只能为（小写字母，数字，下滑线）」
       （文案里「下滑线」是后端错别字，原文如此）
    5.1 已知后端缺陷：dictType 传**空串**时，报错文案在「字典类型不能为空」和上面那条
       格式错误之间随机跳变（实测 6 次里 2 次是格式错误），
       应该是 @NotBlank 和格式正则两个校验的先后顺序不确定。
       所以对空串不要硬断言具体文案；传 null 或不传 key 时文案稳定是「不能为空」。
    6. 【重要】如果该类型下已分配字典数据，删除会被拒：
       code=500，msg「{dictName}已分配,不能删除」（逗号是半角）
    """

    @staticmethod
    def get_list(token, dict_name=None, dict_type=None, page_size=100):
        """查询字典类型列表，返回响应对象。
        page_size 默认 100，避免分页漏数据（这个接口分页是真的生效的）。"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {"pageNum": 1, "pageSize": page_size}
        if dict_name is not None:
            params["dictName"] = dict_name
        if dict_type is not None:
            params["dictType"] = dict_type
        return requests.get(
            f"{API_BASE_URL}/system/dict/type/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def get_by_id(token, dict_id):
        """按 id 查询单个字典类型，返回响应对象。
        查不存在的 id 返回 code=200 且无 data 字段（物理删除）"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(f"{API_BASE_URL}/system/dict/type/{dict_id}", headers=headers)

    @staticmethod
    def add(token, dict_name, dict_type, status="0"):
        """新增字典类型，返回响应对象。
        dict_name / dict_type 必填，缺了分别报「字典名称不能为空」「字典类型不能为空」；
        dict_type 必须是字母开头的（小写字母，数字，下划线），否则报格式错误；
        dict_type 唯一，重复报「字典类型已存在」；
        status 不传也能建成功，后端默认给 "0"（正常）"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "dictName": dict_name,
            "dictType": dict_type,
            "status": status,
        }
        return requests.post(
            f"{API_BASE_URL}/system/dict/type",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def update(token, dict_id, dict_name, dict_type, status="0"):
        """修改字典类型，返回响应对象。dict_id 必填。
        注意 dict_type 改了以后，引用它的字典数据不会跟着改"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "dictId": dict_id,
            "dictName": dict_name,
            "dictType": dict_type,
            "status": status,
        }
        return requests.put(
            f"{API_BASE_URL}/system/dict/type",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def delete(token, dict_id):
        """删除字典类型，返回响应对象。注意字典类型删除是**物理删除**
        （sys_dict_type 表没有 del_flag 列），删后列表查不到，按 id 单查也不会再有 data。

        被引用时返回 code=500，msg 形如「xxx已分配,不能删除」（逗号是半角）——
        注意这个模块用 500 报业务冲突，跟部门/菜单的 601 不是一套码。"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.delete(
            f"{API_BASE_URL}/system/dict/type/{dict_id}",
            headers=headers,
        )