"""字典数据相关接口封装"""
import requests
from config import API_BASE_URL


class DictDataApi:
    """字典数据接口。

    探路确认的几个特点（与字典类型模块刻意对照）：
    1. 列表是标准的 {total, rows, code, msg}，**分页有效**（pageSize / pageNum 都生效）；
       过滤条件支持 dictType（精确）、dictLabel（like 模糊）、status（精确），
       固定按 dict_sort 升序返回。
    2. sys_dict_data **没有 del_flag 列**（全表只有 dict_code 一个主键索引），
       删除是**物理删除**，删完按 id 单查也不会再有 data。
    3. dictLabel / dictValue / dictType 三个都是必填（实体上 @NotBlank），
       **dictSort 不是必填**，不传就走 DB 默认值。
       注意 JSON 字段名是 dictSort，前端传的 order 会被静默忽略。
    4. 【重点】用**不存在的 dictType** 建数据会**建成功** ——
       后端不做引用完整性校验，两表之间也没有外键，
       会在库里留下一条挂不到任何类型上的「孤儿数据」（列表里照样查得到）。
       也就是说「字典数据依赖字典类型」这条依赖**只靠调用方自觉**，
       所以每条造数的用例第一步都必须先建类型。
    5. 同一 dictType 下 dictValue **不唯一**（表上没有 dict_value 唯一索引，后端也不查重），
       重复值会老老实实落两条。
    6. dictType 在字典类型模块有正则格式校验，在**字典数据模块没有** ——
       大写 / 短横线 / 点号 / 数字开头 / 中文 全都能建成功。
    7. 【后端缺陷】删除一个**不存在**的 dictCode 会抛 NPE：
       SysDictDataServiceImpl.deleteDictDataByIds 先 selectDictDataById 拿到 null，
       紧接着调 data.getDictType() 就炸了，被全局异常处理器兜成
       code=500 且 **msg 是 null**（不是中文提示）。注意这个模块用 500 报错。
    """

    @staticmethod
    def get_list(token, dict_type=None, dict_label=None, status=None, page_size=100):
        """查询字典数据列表，返回响应对象。
        page_size 默认 100，避免分页漏数据（这个接口分页是真的生效的）。
        dict_label 是 like 模糊匹配，其余是精确匹配。"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {"pageNum": 1, "pageSize": page_size}
        if dict_type is not None:
            params["dictType"] = dict_type
        if dict_label is not None:
            params["dictLabel"] = dict_label
        if status is not None:
            params["status"] = status
        return requests.get(
            f"{API_BASE_URL}/system/dict/data/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def get_by_id(token, dict_code):
        """按 id 查询单条字典数据，返回响应对象。
        查不存在的 dict_code 返回 code=200 且无 data 字段（物理删除）"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(
            f"{API_BASE_URL}/system/dict/data/{dict_code}", headers=headers
        )

    @staticmethod
    def add(token, dict_type, dict_label, dict_value, dict_sort=1, status="0"):
        """新增字典数据，返回响应对象。
        dict_type / dict_label / dict_value 三个必填，缺了分别报
        「字典类型不能为空」「字典标签不能为空」「字典键值不能为空」；
        dict_sort 不是必填；status 不传后端默认给 "0"。

        注意：dict_type **不会**校验是否真实存在，传一个不存在的类型也能建成功。"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "dictType": dict_type,
            "dictLabel": dict_label,
            "dictValue": dict_value,
            "dictSort": dict_sort,
            "status": status,
        }
        return requests.post(
            f"{API_BASE_URL}/system/dict/data",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def update(token, dict_code, dict_type, dict_label, dict_value,
               dict_sort=1, status="0"):
        """修改字典数据，返回响应对象。dict_code 必填。
        改 dict_type 的话数据会直接挂到新类型下（同样不校验新类型是否存在）。"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "dictCode": dict_code,
            "dictType": dict_type,
            "dictLabel": dict_label,
            "dictValue": dict_value,
            "dictSort": dict_sort,
            "status": status,
        }
        return requests.put(
            f"{API_BASE_URL}/system/dict/data",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def delete(token, dict_code):
        """删除字典数据，返回响应对象。字典数据删除是**物理删除**
        （sys_dict_data 表没有 del_flag 列），删后列表查不到，按 id 单查也不会再有 data。

        传一个**不存在**的 dict_code 会走后端 NPE 分支：
        code=500 且 msg 为 null。"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.delete(
            f"{API_BASE_URL}/system/dict/data/{dict_code}",
            headers=headers,
        )
