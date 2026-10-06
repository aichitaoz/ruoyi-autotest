"""接口测试：字典类型"""
import requests
from api.dict_type_api import DictTypeApi
from config import API_BASE_URL

# dictType 格式校验的报错文案。注意「下滑线」是后端的错别字，原文如此
DICT_TYPE_FORMAT_MSG = "字典类型必须以字母开头，且只能为（小写字母，数字，下滑线）"


def _get_dict_id(token, dict_type):
    """从列表里按 dictType 取 dictId，取不到直接报错（比 next 抛 StopIteration 好定位）"""
    list_r = DictTypeApi.get_list(token)
    rows = list_r.json()["rows"]
    hit = [d["dictId"] for d in rows if d["dictType"] == dict_type]
    assert hit, f"列表里找不到字典类型 {dict_type}，现有：{[d['dictType'] for d in rows]}"
    return hit[0]


def _get_dict_types(token):
    """所有字典类型的 dictType 列表，方便做「存在 / 不存在」断言"""
    return [d["dictType"] for d in DictTypeApi.get_list(token).json()["rows"]]


def test_get_dict_type_list(token):
    """查询字典类型列表，应该返回 total 和 rows"""
    r = DictTypeApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert body["total"] >= 1          # 至少有 sys_user_sex 这几个内置字典
    assert isinstance(body["rows"], list)
    # 每个字典类型必须有 dictId / dictName / dictType
    for row in body["rows"]:
        assert "dictId" in row
        assert "dictName" in row
        assert "dictType" in row


def test_add_dict_type(token):
    """新增字典类型，应该成功，且能在列表里查到"""
    r = DictTypeApi.add(token, "autotest类型01", "autotest_type_01")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 回查：新增后必须能在列表里找到
    rows = DictTypeApi.get_list(token).json()["rows"]
    types = [d["dictType"] for d in rows]
    assert "autotest_type_01" in types, f"新增后列表里找不到该类型，现有：{types}"


def test_get_dict_type_by_id(token):
    """按 id 查询字典类型，应该返回该类型的完整信息"""
    # 1. 先建一个
    add_r = DictTypeApi.add(token, "autotest类型查详情", "autotest_type_getone")
    assert add_r.json()["code"] == 200

    # 2. 从列表拿 dictId
    dict_id = _get_dict_id(token, "autotest_type_getone")

    # 3. 按 id 查
    r = DictTypeApi.get_by_id(token, dict_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"
    assert body["data"]["dictId"] == dict_id
    assert body["data"]["dictName"] == "autotest类型查详情"
    assert body["data"]["dictType"] == "autotest_type_getone"
    assert body["data"]["status"] == "0"


def test_update_dict_type(token):
    """修改字典名称，应该成功，且改后能查到新值"""
    # 1. 先建一个
    DictTypeApi.add(token, "autotest类型改前", "autotest_type_update")

    # 2. 从列表里找到它的 dictId
    dict_id = _get_dict_id(token, "autotest_type_update")

    # 3. 改字典名称（dictType 保持不变）
    r = DictTypeApi.update(token, dict_id, "autotest类型改后", "autotest_type_update")
    assert r.status_code == 200
    assert r.json()["code"] == 200
    assert r.json()["msg"] == "操作成功"

    # 4. 回查，确认改了
    detail_r = DictTypeApi.get_by_id(token, dict_id)
    assert detail_r.json()["data"]["dictName"] == "autotest类型改后"
    assert detail_r.json()["data"]["dictType"] == "autotest_type_update"


def test_delete_dict_type(token):
    """删除字典类型，应该成功，且列表里查不到（物理删除，验证必须走列表接口）"""
    # 1. 先建一个
    DictTypeApi.add(token, "autotest类型待删", "autotest_type_todelete")

    # 2. 从列表拿 dictId
    dict_id = _get_dict_id(token, "autotest_type_todelete")

    # 3. 删
    r = DictTypeApi.delete(token, dict_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 4. 回查：列表里应该查不到
    types = _get_dict_types(token)
    assert "autotest_type_todelete" not in types, f"删除后列表里仍能查到该类型：{types}"

    # 5. 物理删除的标志：按 id 单查也不会再有 data 字段
    detail_r = DictTypeApi.get_by_id(token, dict_id)
    assert detail_r.json()["code"] == 200
    assert "data" not in detail_r.json(), f"字典类型是物理删除，单查不该再有 data：{detail_r.json()}"


def test_add_duplicate_dict_type(token):
    """重复新增同 dictType 的字典类型，应该被拒（dictType 唯一，dictName 不唯一）"""
    # 1. 建第一个
    r1 = DictTypeApi.add(token, "autotest类型重复", "autotest_type_dup")
    assert r1.json()["code"] == 200

    # 2. 再建同 dictType，换个 dictName，应该失败
    r2 = DictTypeApi.add(token, "autotest类型重复2", "autotest_type_dup")
    assert r2.status_code == 200
    body = r2.json()
    assert body["code"] != 200, f"重复 dictType 应该被拒绝，实际返回：{body}"
    assert "字典类型已存在" in body["msg"]

    # 3. 回查：列表里只能有一个 autotest_type_dup，且名字还是第一个的
    rows = DictTypeApi.get_list(token).json()["rows"]
    dups = [d for d in rows if d["dictType"] == "autotest_type_dup"]
    assert len(dups) == 1, f"同 dictType 只应存在一条，实际 {len(dups)} 条"
    assert dups[0]["dictName"] == "autotest类型重复"


def test_add_dict_type_with_duplicate_name(token):
    """dictName 不唯一 —— 反向锁住这个行为（跟 dictType 唯一形成对比）"""
    # 1. 建第一个
    r1 = DictTypeApi.add(token, "autotest类型重名", "autotest_type_name_a")
    assert r1.json()["code"] == 200

    # 2. 用同一个 dictName 但换dictType，应该成功
    r2 = DictTypeApi.add(token, "autotest类型重名", "autotest_type_name_b")
    assert r2.status_code == 200
    body = r2.json()
    assert body["code"] == 200, f"dictName 不唯一，这里期望成功，实际：{body}"

    # 3. 回查：两条都在，dictName 相同、dictType 不同
    rows = DictTypeApi.get_list(token).json()["rows"]
    same = [d for d in rows if d["dictName"] == "autotest类型重名"]
    assert len(same) == 2, f"同名字典类型应能有 2 条，实际 {len(same)} 条"
    assert {d["dictType"] for d in same} == {"autotest_type_name_a", "autotest_type_name_b"}


def test_add_dict_type_without_required_fields(token):
    """新增字典类型缺必填字段，应该被拒并给出对应中文提示。

    注意一个后端的坑：dictType 传**空串**时，报错文案在「字典类型不能为空」和
    「字典类型必须以字母开头...」之间**随机跳变**（实测 6 次里有 2 次给的是格式错误）。
    应该是 @NotBlank 和格式正则两个校验的先后顺序不确定，属于后端缺陷。
    所以这里不断言具体文案，只断言「被拒了 + 报错是这两条之一」；
    而 dictName 传空串的文案是稳定的，可以硬断言。"""
    # 1. dictName 为空 -> 文案稳定，可以硬断言
    r1 = DictTypeApi.add(token, "", "autotest_type_noname")
    assert r1.status_code == 200
    assert r1.json()["code"] == 500
    assert r1.json()["msg"] == "字典名称不能为空"

    # 2. dictType 为空串 -> 可能报「不能为空」也可能报「格式错误」，两者都算被拒
    r2 = DictTypeApi.add(token, "autotest类型无标识", "")
    assert r2.status_code == 200
    assert r2.json()["code"] == 500
    assert r2.json()["msg"] in ("字典类型不能为空", DICT_TYPE_FORMAT_MSG), \
        f"dictType 为空应被拒，实际报错：{r2.json()['msg']}"

    # 3. dictType 传 null -> 文案稳定是「不能为空」
    r3 = requests.post(
        f"{API_BASE_URL}/system/dict/type",
        headers={"Authorization": f"Bearer {token}"},
        json={"dictName": "autotest类型标识为null", "dictType": None},
    )
    assert r3.status_code == 200
    assert r3.json()["code"] == 500
    assert r3.json()["msg"] == "字典类型不能为空"

    # 4. 回查：这些失败的新增都不该落库
    rows = DictTypeApi.get_list(token).json()["rows"]
    types = [d["dictType"] for d in rows]
    assert "autotest_type_noname" not in types, f"校验失败的类型却落库了，现有：{types}"


def test_add_dict_type_with_invalid_format(token):
    """dictType 不只是非空校验，还有**格式校验**：
    必须以字母开头，且只能是（小写字母，数字，下滑线）—— 注意「下滑线」是后端的错别字，原文如此。
    数字开头 / 含大写 / 含短横线 / 含点号 / 下划线开头，全部会被拒。"""
    # 逐个试各种不合法格式
    for tag, bad_type in [
        ("数字开头", "1autotest"),
        ("含大写", "Autotest"),
        ("含短横线", "autotest-bad"),
        ("含点号", "autotest.bad"),
        ("下划线开头", "_autotest"),
    ]:
        r = DictTypeApi.add(token, f"autotest格式{tag}", bad_type)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 500, f"dictType={bad_type!r}（{tag}）应被拒绝，实际：{body}"
        assert body["msg"] == DICT_TYPE_FORMAT_MSG, f"dictType={bad_type!r} 的报错文案不对：{body['msg']}"

    # 合法格式（字母开头的全小写下划线）应该能建
    ok = DictTypeApi.add(token, "autotest格式合法", "autotest_ok_1")
    assert ok.json()["code"] == 200, f"合法 dictType 应能建成功，实际：{ok.json()}"

    # 回查：不合法的都没落库，合法的落了
    types = _get_dict_types(token)
    for bad in ["1autotest", "Autotest", "autotest-bad", "autotest.bad", "_autotest"]:
        assert bad not in types, f"格式不合法的 {bad!r} 却落库了"
    assert "autotest_ok_1" in types


def test_delete_dict_type_referenced_rejected(token):
    """删除已被字典数据引用的字典类型，应该被拒（code=500，msg 带类型名）。

    这条约束用的是 500，不是部门/菜单那种 601，是这个模块特有的。
    也正因为用的是500 且 msg 里嵌了类型名，断言要用 in 而不是等号比较。"""
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 建一个字典类型
    add_r = DictTypeApi.add(token, "autotest被引用类型", "autotest_type_referenced")
    assert add_r.json()["code"] == 200
    dict_id = _get_dict_id(token, "autotest_type_referenced")

    # 2. 直接往 sys_dict_data 塞一条数据引用它（字典数据模块的正式封装下一轮再写）
    data_r = requests.post(
        f"{API_BASE_URL}/system/dict/data",
        headers=headers,
        json={
            "dictType": "autotest_type_referenced",
            "dictLabel": "autotest引用标签",
            "dictValue": "autotest_ref_val",
            "order": 1,
            "status": "0",
        },
    )
    assert data_r.json()["code"] == 200, f"造引用数据失败：{data_r.json()}"

    # 3. 删这个类型，应该被拒
    r = DictTypeApi.delete(token, dict_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] != 200, f"被引用的类型不该删成功，实际返回：{body}"
    assert "已分配,不能删除" in body["msg"]
    # msg 里带上了被删类型的名字
    assert "autotest被引用类型" in body["msg"]

    # 4. 回查：类型还在列表里
    assert "autotest_type_referenced" in _get_dict_types(token)

    # 5. 收尾：先删引用数据，再删类型，避免给其他用例留垃圾数据
    data_list = requests.get(
        f"{API_BASE_URL}/system/dict/data/list",
        headers=headers,
        params={"pageNum": 1, "pageSize": 100},
    ).json()
    codes = [x["dictCode"] for x in data_list["rows"]
             if x["dictType"] == "autotest_type_referenced"]
    assert codes, "引用数据应该还在"
    for c in codes:
        requests.delete(f"{API_BASE_URL}/system/dict/data/{c}", headers=headers)

    # 6. 清掉引用后，类型就能删了
    r2 = DictTypeApi.delete(token, dict_id)
    assert r2.json()["code"] == 200, f"清掉引用后应该能删，实际：{r2.json()}"
    assert "autotest_type_referenced" not in _get_dict_types(token)


def test_get_dict_type_list_with_pagination(token):
    """分页查询，pageSize=1 时返回条数不超过 1（这个接口分页是真的生效的）"""
    r = DictTypeApi.get_list(token, page_size=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)
    assert len(body["rows"]) <= 1, f"pageSize=1 却返回了 {len(body['rows'])} 条"
    # total 是满足条件的总条数，不受 pageSize 影响，应不少于实际返回条数
    assert body["total"] >= len(body["rows"])


def test_get_dict_type_list_with_filter(token):
    """按 dictType 过滤，应该只返回匹配的字典类型"""
    DictTypeApi.add(token, "autotest类型过滤", "autotest_type_filter")

    r = DictTypeApi.get_list(token, dict_type="autotest_type_filter")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["total"] == 1, f"按 dictType 过滤应只返回 1 条，实际 {body['total']} 条"
    assert body["rows"][0]["dictType"] == "autotest_type_filter"
    assert body["rows"][0]["dictName"] == "autotest类型过滤"

    # 筛一个不存在的，应该返回空
    r2 = DictTypeApi.get_list(token, dict_type="autotest_type_not_exist")
    assert r2.json()["total"] == 0, f"筛不存在的 dictType 应返回 0 条，实际 {r2.json()['total']}"