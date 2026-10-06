"""接口测试：字典数据

核心依赖：字典数据挂在字典类型的 dictType 字符串上，
所以**每条造数据的用例，第一步都必须先建一个 dictType 相同的字典类型**。
"""
import requests

from api.dict_data_api import DictDataApi
from api.dict_type_api import DictTypeApi
from config import API_BASE_URL

# 本模块的固定测试数据（前缀 autotest）
TYPE = "autotest_data_type_01"
TYPE_NAME = "autotest字典数据依赖类型"
LABEL = "autotest标签01"
VALUE = "autotest_val_01"

# 必填校验的报错文案（来自实体 SysDictData 上的 @NotBlank）
MSG_NO_LABEL = "字典标签不能为空"
MSG_NO_VALUE = "字典键值不能为空"
MSG_NO_TYPE = "字典类型不能为空"

# 重点关注：用不存在的 dictType 造孤儿数据时用的类型
ORPHAN_TYPE = "autotest_orphan_type_zzz"


def _create_type(token, dict_type=TYPE, dict_name=TYPE_NAME):
    """造字典数据前必须先有 dictType 相同的字典类型 —— 本模块的依赖核心。"""
    r = DictTypeApi.add(token, dict_name, dict_type)
    assert r.json()["code"] == 200, f"前置字典类型创建失败：{r.json()}"


def _purge(token, dict_type=TYPE):
    """用例内收尾：先删该 dictType 下的所有字典数据，再删类型本身。

    为什么必须在用例里清、不能只靠 conftest 的「跑前清」：
    跑前清救不了「跑完到下次开跑之间」这段窗口（2026-10-06 菜单模块白屏的教训）。
    顺序不能反：数据挂在 dict_type 这个字符串上，类型先掉数据就成孤儿了。
    """
    for row in DictDataApi.get_list(token, dict_type=dict_type).json()["rows"]:
        DictDataApi.delete(token, row["dictCode"])
    for t in DictTypeApi.get_list(token, dict_type=dict_type).json()["rows"]:
        DictTypeApi.delete(token, t["dictId"])


def _fresh_type(token, dict_type=TYPE, dict_name=TYPE_NAME):
    """清干净再建类型，保证用例起点是确定的（同一个 dictType 被多条用例复用）"""
    _purge(token, dict_type)
    _create_type(token, dict_type, dict_name)


def _get_code(token, dict_type, dict_value):
    """从列表里按 dictType + dictValue 取 dictCode，取不到直接报错"""
    rows = DictDataApi.get_list(token, dict_type=dict_type).json()["rows"]
    hit = [r["dictCode"] for r in rows if r["dictValue"] == dict_value]
    assert hit, (f"列表里找不到 {dict_type}/{dict_value}，"
                 f"现有：{[(r['dictType'], r['dictValue']) for r in rows]}")
    return hit[0]


def test_get_dict_data_list(token):
    """列表返回标准结构 {total, rows, code, msg}，每行含 dictCode/dictLabel/dictValue/dictType"""
    _fresh_type(token)
    try:
        DictDataApi.add(token, TYPE, LABEL, VALUE)

        r = DictDataApi.get_list(token)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert "total" in body
        assert "rows" in body
        assert isinstance(body["rows"], list)
        assert body["total"] >= 1

        for row in body["rows"]:
            for key in ("dictCode", "dictLabel", "dictValue", "dictType", "dictSort", "status"):
                assert key in row, f"列表行里缺字段 {key}：{row}"

        # 内置字典数据（sys_user_sex 等）应该在里面，说明这是全量而不是空表
        assert "sys_user_sex" in {row["dictType"] for row in body["rows"]}
    finally:
        _purge(token)


def test_add_dict_data(token):
    """新增字典数据：先建类型再建数据，应该成功且能在列表里查到"""
    _fresh_type(token)
    try:
        r = DictDataApi.add(token, TYPE, LABEL, VALUE)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["msg"] == "操作成功"

        # 回查：新增后必须能在列表里找到
        rows = DictDataApi.get_list(token, dict_type=TYPE).json()["rows"]
        hit = [x for x in rows if x["dictValue"] == VALUE]
        assert len(hit) == 1, f"新增后应恰有 1 条 {VALUE}，实际 {len(hit)} 条"
        assert hit[0]["dictLabel"] == LABEL
        assert hit[0]["dictType"] == TYPE
    finally:
        _purge(token)


def test_get_dict_data_by_id(token):
    """按 id 查询单条字典数据，应该返回该条完整信息"""
    _fresh_type(token)
    try:
        add_r = DictDataApi.add(token, TYPE, LABEL, VALUE, dict_sort=3)
        assert add_r.json()["code"] == 200

        dict_code = _get_code(token, TYPE, VALUE)

        r = DictDataApi.get_by_id(token, dict_code)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["msg"] == "操作成功"
        assert body["data"]["dictCode"] == dict_code
        assert body["data"]["dictLabel"] == LABEL
        assert body["data"]["dictValue"] == VALUE
        assert body["data"]["dictType"] == TYPE
        assert body["data"]["dictSort"] == 3
        assert body["data"]["status"] == "0"
    finally:
        _purge(token)


def test_update_dict_data(token):
    """修改字典标签和排序，应该成功，且改后能查到新值"""
    _fresh_type(token)
    try:
        DictDataApi.add(token, TYPE, "autotest标签改前", "autotest_val_update")
        dict_code = _get_code(token, TYPE, "autotest_val_update")

        r = DictDataApi.update(token, dict_code, TYPE, "autotest标签改后",
                               "autotest_val_update", dict_sort=9)
        assert r.status_code == 200
        assert r.json()["code"] == 200
        assert r.json()["msg"] == "操作成功"

        # 回查，确认改了
        data = DictDataApi.get_by_id(token, dict_code).json()["data"]
        assert data["dictLabel"] == "autotest标签改后"
        assert data["dictSort"] == 9
        assert data["dictValue"] == "autotest_val_update"   # 没动的字段不该被改
        assert data["dictType"] == TYPE
    finally:
        _purge(token)


def test_delete_dict_data(token):
    """删除字典数据，应该成功，且列表里查不到（物理删除，验证必须走列表接口）"""
    _fresh_type(token)
    try:
        DictDataApi.add(token, TYPE, LABEL, VALUE)
        dict_code = _get_code(token, TYPE, VALUE)

        r = DictDataApi.delete(token, dict_code)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["msg"] == "操作成功"

        # 老规矩：删除验证走列表接口
        rows = DictDataApi.get_list(token, dict_type=TYPE).json()["rows"]
        assert dict_code not in [x["dictCode"] for x in rows], "删除后列表里仍能查到该条数据"

        # 物理删除的标志：按 id 单查也不会再有 data 字段
        detail = DictDataApi.get_by_id(token, dict_code).json()
        assert detail["code"] == 200
        assert "data" not in detail, f"字典数据是物理删除，单查不该再有 data：{detail}"
    finally:
        _purge(token)


def test_add_dict_data_with_duplicate_value(token):
    """反向锁：同一 dictType 下 dictValue **不唯一**。

    探路实测：表上只有 dict_code 一个主键索引、没有 dict_value 唯一索引，
    后端也没有查重逻辑，所以重复值会老老实实落两条。
    这条和字典类型模块（dictType 唯一，重复报「字典类型已存在」）刻意形成对照。"""
    _fresh_type(token)
    try:
        r1 = DictDataApi.add(token, TYPE, "autotest重复值A", "autotest_dup_val")
        assert r1.json()["code"] == 200

        # 同 dictType、同 dictValue、换个 label —— 期望成功
        r2 = DictDataApi.add(token, TYPE, "autotest重复值B", "autotest_dup_val")
        assert r2.status_code == 200
        assert r2.json()["code"] == 200, f"dictValue 不唯一，这里期望建成功，实际：{r2.json()}"

        # 回查：两条都在，dictValue 相同、dictLabel 不同
        rows = [x for x in DictDataApi.get_list(token, dict_type=TYPE).json()["rows"]
                if x["dictValue"] == "autotest_dup_val"]
        assert len(rows) == 2, f"同 dictValue 应能有 2 条，实际 {len(rows)} 条"
        assert {x["dictLabel"] for x in rows} == {"autotest重复值A", "autotest重复值B"}
    finally:
        _purge(token)


def test_add_dict_data_without_required_fields(token):
    """新增字典数据缺必填字段，应该被拒并给出对应中文提示。

    必填只有 dictType / dictLabel / dictValue 三个，**dictSort 不是必填**。

    一个后端坑：只缺**一个**字段时文案是稳定的，可以硬断言；
    但**同时缺多个**字段时，返回的是哪个字段的报错是**随机**的 ——
    实测「空 JSON」跑 10 次，三种文案都出现过（4/5/1 次）。
    成因是 Hibernate Validator 的校验错误顺序没有契约保证，
    跟字典类型模块里 dictType 空串那个漂移是同一类问题。"""
    _fresh_type(token)
    try:
        # 1. 只缺 dictLabel -> 文案稳定，可以硬断言
        r1 = DictDataApi.add(token, TYPE, "", VALUE)
        assert r1.status_code == 200
        assert r1.json()["code"] == 500
        assert r1.json()["msg"] == MSG_NO_LABEL

        # 2. 只缺 dictValue -> 文案稳定
        r2 = DictDataApi.add(token, TYPE, LABEL, "")
        assert r2.status_code == 200
        assert r2.json()["code"] == 500
        assert r2.json()["msg"] == MSG_NO_VALUE

        # 3. 只缺 dictType -> 文案稳定（这里没有正则校验，所以不像字典类型模块那样会漂到格式错误）
        r3 = DictDataApi.add(token, "", LABEL, VALUE)
        assert r3.status_code == 200
        assert r3.json()["code"] == 500
        assert r3.json()["msg"] == MSG_NO_TYPE

        # 4. 三个 key 全不传 -> 报错文案随机，只断言「被拒 + 是这三条之一」
        r4 = requests.post(
            f"{API_BASE_URL}/system/dict/data",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert r4.status_code == 200
        assert r4.json()["code"] == 500
        assert r4.json()["msg"] in (MSG_NO_LABEL, MSG_NO_VALUE, MSG_NO_TYPE), \
            f"全缺应被拒，实际报错：{r4.json()['msg']}"

        # 5. 反向对照：只有三个必填、不传 dictSort 也能建成功
        ok = DictDataApi.add(token, TYPE, LABEL, VALUE)
        assert ok.json()["code"] == 200, f"dictSort 不是必填，应能建成功，实际：{ok.json()}"

        # 6. 回查：校验失败的那几条都不该落库，该类型下只剩最后那条合法的
        rows = DictDataApi.get_list(token, dict_type=TYPE).json()["rows"]
        assert len(rows) == 1, f"该类型下只应剩 1 条合法数据，实际 {len(rows)} 条"
    finally:
        _purge(token)


def test_add_dict_data_with_nonexistent_dict_type(token):
    """【重点异常场景】用不存在的 dictType 建字典数据。

    实测结论：后端**不做引用完整性校验**，sys_dict_data 上也没有指向 sys_dict_type
    的外键，所以**会建成功**，在库里留下一条挂不到任何类型上的「孤儿数据」
    （列表里照样查得到，按 dictType 过滤也能筛出来）。

    这里如实锁住这个行为 —— 它正是「字典数据依赖字典类型」这条依赖
    **只靠调用方自觉**的证据，也是每条造数用例第一步都必须先建类型的原因。"""
    _purge(token, ORPHAN_TYPE)
    try:
        # 先确认这个类型真的不存在
        assert DictTypeApi.get_list(token, dict_type=ORPHAN_TYPE).json()["total"] == 0, \
            f"{ORPHAN_TYPE} 不该存在（前置清理失败）"

        r = DictDataApi.add(token, ORPHAN_TYPE, "autotest孤儿标签", "autotest_orphan_val")
        assert r.status_code == 200
        assert r.json()["code"] == 200, \
            f"后端不校验 dictType 存在性，这里会建成功，实际：{r.json()}"

        # 回查：孤儿数据确实落库了
        body = DictDataApi.get_list(token, dict_type=ORPHAN_TYPE).json()
        assert body["total"] == 1, f"孤儿数据应落库 1 条，实际 {body['total']} 条"
        assert body["rows"][0]["dictType"] == ORPHAN_TYPE
        assert body["rows"][0]["dictLabel"] == "autotest孤儿标签"

        # 补一刀：这个 dictType 在类型表里依然查不到，说明数据确实是孤儿
        assert DictTypeApi.get_list(token, dict_type=ORPHAN_TYPE).json()["total"] == 0
    finally:
        _purge(token, ORPHAN_TYPE)


def test_add_dict_data_dict_type_without_format_check(token):
    """对照字典类型模块：字典数据的 dictType 字段**没有正则格式校验**。

    字典类型模块里 dictType 必须「字母开头，且只能是（小写字母，数字，下划线）」，
    大写 / 短横线 / 点号 / 数字开头 全会被拒；
    但 SysDictData 上的 dictType 只有 @NotBlank + @Size(max=100)，没有 @Pattern，
    所以这些写法在**字典数据模块全部能建成功**。
    也就是说可以造出各种「假 dictType」的孤儿数据。"""
    bad_types = [
        ("大写", "Autotest_Bad_Upper"),
        ("短横线", "autotest-bad-type"),
        ("点号", "autotest.bad.type"),
        ("数字开头", "1autotest"),
        ("中文", "自动测试类型"),
    ]
    for _, bad in bad_types:
        _purge(token, bad)
    try:
        for idx, (tag, bad) in enumerate(bad_types):
            r = DictDataApi.add(token, bad, f"autotest格式{tag}", f"autotest_fv_{idx}")
            assert r.status_code == 200
            assert r.json()["code"] == 200, \
                f"dictType={bad!r}（{tag}）在字典数据模块应能建成功（无格式校验），实际：{r.json()}"

            # 回查：确实落库了
            assert DictDataApi.get_list(token, dict_type=bad).json()["total"] == 1
    finally:
        for _, bad in bad_types:
            _purge(token, bad)


def test_delete_nonexistent_dict_data(token):
    """删除一个不存在的 dictCode —— 后端会崩（NPE），code=500 且 msg 是 null。

    成因：SysDictDataServiceImpl.deleteDictDataByIds 先 selectDictDataById(dictCode)，
    查不到拿到 null，紧接着调 data.getDictType() 抛 NPE，
    被全局异常处理器兜成 500。注意这里的 msg 是 **null**（不是中文提示），
    跟前面那些业务校验失败（msg 是中文）不是一回事。"""
    r = DictDataApi.delete(token, 99999999)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 500, f"删不存在的 dictCode 应该失败，实际：{body}"
    assert body["msg"] is None, f"这条 NPE 路径的 msg 是 null，实际：{body['msg']!r}"


def test_get_dict_data_list_with_pagination(token):
    """分页有效：pageSize 限制返回条数，total 不受 pageSize 影响"""
    r = DictDataApi.get_list(token, page_size=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)
    assert len(body["rows"]) <= 1, f"pageSize=1 却返回了 {len(body['rows'])} 条"
    assert body["total"] >= len(body["rows"])

    body2 = DictDataApi.get_list(token, page_size=2).json()
    assert len(body2["rows"]) <= 2, f"pageSize=2 却返回了 {len(body2['rows'])} 条"
    assert body2["total"] == body["total"], "total 不该受 pageSize 影响"


def test_get_dict_data_list_with_filter(token):
    """筛选：dictType 精确匹配、dictLabel 模糊匹配，筛不存在的条件返回 0"""
    _fresh_type(token)
    try:
        DictDataApi.add(token, TYPE, LABEL, VALUE)

        # 按 dictType 精确过滤
        body = DictDataApi.get_list(token, dict_type=TYPE).json()
        assert body["code"] == 200
        assert body["total"] == 1, f"按 dictType 过滤应只返回 1 条，实际 {body['total']} 条"
        assert body["rows"][0]["dictType"] == TYPE
        assert body["rows"][0]["dictLabel"] == LABEL

        # dictLabel 是 like 模糊匹配
        body2 = DictDataApi.get_list(token, dict_label="autotest标签").json()
        assert body2["total"] >= 1
        assert all("autotest标签" in x["dictLabel"] for x in body2["rows"])

        # 筛不存在的 dictType，应该返回 0
        assert DictDataApi.get_list(token, dict_type="autotest_zzz_none").json()["total"] == 0
    finally:
        _purge(token)
