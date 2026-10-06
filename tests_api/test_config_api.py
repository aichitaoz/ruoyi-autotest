"""接口测试：参数配置"""
from api.config_api import ConfigApi

# 本模块的固定测试数据（前缀 autotest）
KEY = "autotest.config.key"
NAME = "autotest配置01"
VALUE = "autotest_value_01"

# configKey 的过滤是 like 模糊匹配，用 autotest 一把能把本模块造的数据都捞出来
KEY_PREFIX = "autotest"

# 必填校验的报错文案（来自实体 SysConfig 上的 @NotBlank）
# 注意 MSG_NO_KEY 里「长度」两个字是后端文案瑕疵，原文如此
MSG_NO_KEY = "参数键名长度不能为空"
MSG_NO_NAME = "参数名称不能为空"
MSG_NO_VALUE = "参数键值不能为空"


def _purge(token):
    """用例内收尾：删掉所有 autotest 前缀的参数配置。

    为什么必须在用例里清、不能只靠 conftest 的「跑前清」：
    跑前清救不了「跑完到下次开跑之间」这段窗口（2026-10-06 菜单模块白屏的教训）。
    """
    rows = ConfigApi.get_list(token, config_key=KEY_PREFIX, page_size=100).json()["rows"]
    for row in rows:
        ConfigApi.delete(token, row["configId"])


def _fresh(token):
    """清干净，保证用例起点是确定的"""
    _purge(token)
    left = ConfigApi.get_list(token, config_key=KEY_PREFIX, page_size=100).json()["total"]
    assert left == 0, f"前置清理没干净，还剩 {left} 条 autotest 参数"


def _get_config_id(token, config_key):
    """从列表里按 configKey 取 configId，取不到直接报错"""
    rows = ConfigApi.get_list(token, config_key=config_key, page_size=100).json()["rows"]
    hit = [r["configId"] for r in rows if r["configKey"] == config_key]
    assert hit, (f"列表里找不到 configKey={config_key}，"
                 f"现有：{[r['configKey'] for r in rows]}")
    return hit[0]


def test_get_config_list(token):
    """列表返回标准结构 {total, rows, code, msg}，每行含必要字段"""
    r = ConfigApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)
    assert body["total"] >= 1

    for row in body["rows"]:
        for key in ("configId", "configName", "configKey", "configValue", "configType"):
            assert key in row, f"列表行里缺字段 {key}：{row}"

    # 内置参数应该在里面
    assert "sys.index.skinName" in {row["configKey"] for row in body["rows"]}


def test_add_config(token):
    """新增参数配置，应该成功，且能在列表里查到"""
    _fresh(token)
    try:
        r = ConfigApi.add(token, KEY, NAME, VALUE)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["msg"] == "操作成功"

        # 回查：新增后必须能在列表里找到
        rows = ConfigApi.get_list(token, config_key=KEY, page_size=100).json()["rows"]
        hit = [x for x in rows if x["configKey"] == KEY]
        assert len(hit) == 1, f"新增后应恰有 1 条 {KEY}，实际 {len(hit)} 条"
        assert hit[0]["configName"] == NAME
        assert hit[0]["configValue"] == VALUE
    finally:
        _purge(token)


def test_get_config_by_id(token):
    """按 id 查询单条参数配置，应该返回该条完整信息"""
    _fresh(token)
    try:
        assert ConfigApi.add(token, KEY, NAME, VALUE).json()["code"] == 200
        config_id = _get_config_id(token, KEY)

        r = ConfigApi.get_by_id(token, config_id)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["msg"] == "操作成功"
        assert body["data"]["configId"] == config_id
        assert body["data"]["configKey"] == KEY
        assert body["data"]["configName"] == NAME
        assert body["data"]["configValue"] == VALUE
    finally:
        _purge(token)


def test_update_config(token):
    """修改参数名称和键值，应该成功，且改后能查到新值"""
    _fresh(token)
    try:
        ConfigApi.add(token, KEY, "autotest配置改前", "autotest_value_before")
        config_id = _get_config_id(token, KEY)

        r = ConfigApi.update(token, config_id, KEY, "autotest配置改后", "autotest_value_after")
        assert r.status_code == 200
        assert r.json()["code"] == 200
        assert r.json()["msg"] == "操作成功"

        # 回查，确认改了
        data = ConfigApi.get_by_id(token, config_id).json()["data"]
        assert data["configName"] == "autotest配置改后"
        assert data["configValue"] == "autotest_value_after"
        assert data["configKey"] == KEY          # 没动的字段不该被改
    finally:
        _purge(token)


def test_update_config_must_send_config_key(token):
    """修改时 @Validated 作用在整个请求体上，所以**必须带上 configKey**。
    只传 configId + configValue 会被必填校验拦下（报「参数键名长度不能为空」），
    这条锁住「update 的 payload 不能精简」这个容易踩的坑。"""
    _fresh(token)
    try:
        ConfigApi.add(token, KEY, NAME, VALUE)
        config_id = _get_config_id(token, KEY)

        # 故意只传 configId + configValue
        r = ConfigApi.update(token, config_id, "", "", "autotest_value_z")
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 500, f"缺 configKey 应被必填校验拦下，实际：{body}"

        # 回查：数据没被改动
        data = ConfigApi.get_by_id(token, config_id).json()["data"]
        assert data["configKey"] == KEY
        assert data["configValue"] == VALUE
    finally:
        _purge(token)


def test_delete_config(token):
    """删除参数配置，应该成功，且列表里查不到（物理删除，验证必须走列表接口）"""
    _fresh(token)
    try:
        ConfigApi.add(token, KEY, NAME, VALUE)
        config_id = _get_config_id(token, KEY)

        r = ConfigApi.delete(token, config_id)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["msg"] == "操作成功"

        # 老规矩：删除验证走列表接口
        rows = ConfigApi.get_list(token, config_key=KEY_PREFIX, page_size=100).json()["rows"]
        assert config_id not in [x["configId"] for x in rows], "删除后列表里仍能查到"

        # 物理删除的标志：按 id 单查也不会再有 data 字段
        detail = ConfigApi.get_by_id(token, config_id).json()
        assert detail["code"] == 200
        assert "data" not in detail, f"参数配置是物理删除，单查不该再有 data：{detail}"
    finally:
        _purge(token)


def test_add_config_with_duplicate_key(token):
    """重复新增同 configKey 的参数，应该被拒（configKey 唯一，但唯一性是代码层做的）"""
    _fresh(token)
    try:
        r1 = ConfigApi.add(token, KEY, "autotest配置重复1", VALUE)
        assert r1.json()["code"] == 200

        # 换个 configName，configKey 不变 -> 应该失败
        r2 = ConfigApi.add(token, KEY, "autotest配置重复2", "autotest_value_dup")
        assert r2.status_code == 200
        body = r2.json()
        assert body["code"] != 200, f"重复 configKey 应该被拒绝，实际返回：{body}"
        assert "参数键名已存在" in body["msg"], f"报错文案不对：{body['msg']}"
        # msg 里嵌了参数名，用 in 而不是等号
        assert "autotest配置重复2" in body["msg"]

        # 回查：同 configKey 只应有一条，且还是第一条的值
        rows = [x for x in ConfigApi.get_list(token, config_key=KEY_PREFIX,
                                              page_size=100).json()["rows"]
                if x["configKey"] == KEY]
        assert len(rows) == 1, f"同 configKey 只应存在一条，实际 {len(rows)} 条"
        assert rows[0]["configName"] == "autotest配置重复1"
    finally:
        _purge(token)


def test_update_config_to_duplicate_key(token):
    """修改时把 configKey 改成别人已占用的，应该被拒（注意：改成自己原来的 key 是允许的）"""
    _fresh(token)
    try:
        other_key = KEY + "_b"
        ConfigApi.add(token, KEY, "autotest配置主", VALUE)
        ConfigApi.add(token, other_key, "autotest配置次", "autotest_value_b")
        main_id = _get_config_id(token, KEY)

        # 把主的 configKey 改成次的 -> 冲突，应被拒
        r = ConfigApi.update(token, main_id, other_key, "autotest配置主", VALUE)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] != 200, f"改成已占用的 configKey 应被拒，实际：{body}"
        assert "参数键名已存在" in body["msg"], f"报错文案不对：{body['msg']}"

        # 回查：key 没被改掉
        assert ConfigApi.get_by_id(token, main_id).json()["data"]["configKey"] == KEY

        # 反向对照：改成自己原来的 key 是允许的（checkConfigKeyUnique 会排除自身）
        ok = ConfigApi.update(token, main_id, KEY, "autotest配置主改", VALUE)
        assert ok.json()["code"] == 200, f"改成自己原来的 key 应允许，实际：{ok.json()}"
        assert ConfigApi.get_by_id(token, main_id).json()["data"]["configName"] == "autotest配置主改"
    finally:
        _purge(token)


def test_add_config_without_required_fields(token):
    """新增参数配置缺必填字段，应该被拒并给出对应中文提示。
    configKey / configName / configValue 三个必填，configType 不是必填。"""
    _fresh(token)
    try:
        # 只缺 configName -> 文案稳定
        r1 = ConfigApi.add(token, KEY, "", VALUE)
        assert r1.status_code == 200
        assert r1.json()["code"] == 500
        assert r1.json()["msg"] == MSG_NO_NAME

        # 只缺 configKey -> 文案稳定（「参数键名长度不能为空」，原文如此）
        r2 = ConfigApi.add(token, "", NAME, VALUE)
        assert r2.status_code == 200
        assert r2.json()["code"] == 500
        assert r2.json()["msg"] == MSG_NO_KEY

        # 只缺 configValue -> 文案稳定
        r3 = ConfigApi.add(token, KEY, NAME, "")
        assert r3.status_code == 200
        assert r3.json()["code"] == 500
        assert r3.json()["msg"] == MSG_NO_VALUE

        # 回查：校验失败的都不该落库
        assert ConfigApi.get_list(token, config_key=KEY_PREFIX, page_size=100).json()["total"] == 0
    finally:
        _purge(token)


def test_add_config_config_type_is_not_required(token):
    """configType 不是必填 —— 不传也能建成功，后端存 DB 默认值 "N"（非系统内置）。

    这条同时解释了为什么「自建参数能被删」：删内置参数（configType="Y"）是被禁止的，
    而我们不传 configType 建出来的都是 "N"，所以不在保护范围内。"""
    _fresh(token)
    try:
        r = ConfigApi.add(token, KEY, NAME, VALUE)
        assert r.json()["code"] == 200, f"configType 不是必填，应能建成功，实际：{r.json()}"

        data = ConfigApi.get_by_id(token, _get_config_id(token, KEY)).json()["data"]
        assert data["configType"] == "N", f"不传 configType 应默认成 N，实际 {data['configType']!r}"
    finally:
        _purge(token)


def test_delete_builtin_config_rejected(token):
    """configType="Y" 的内置参数**不允许删除**，应报「内置参数【xxx】不能删除」。

    这条用自建的参数来验（configType 传 "Y"），测完把 configType 改回 "N" 再正常删掉，
    全程走接口、不动内置数据、不留垃圾。
    注意报错文案末尾带一个空格，所以用 in 断言而不是等号。"""
    _fresh(token)
    config_id = None
    try:
        r = ConfigApi.add(token, KEY, NAME, VALUE, config_type="Y")
        assert r.json()["code"] == 200, f"前置创建内置参数失败：{r.json()}"
        config_id = _get_config_id(token, KEY)

        d = ConfigApi.delete(token, config_id)
        assert d.status_code == 200
        body = d.json()
        assert body["code"] == 500, f"内置参数不该删成功，实际：{body}"
        assert "内置参数" in body["msg"], f"报错文案不含「内置参数」：{body['msg']!r}"
        assert KEY in body["msg"], f"报错文案里应带上参数键名：{body['msg']!r}"

        # 回查：还在列表里
        assert config_id in [x["configId"] for x in
                             ConfigApi.get_list(token, config_key=KEY_PREFIX,
                                                page_size=100).json()["rows"]]
    finally:
        # 内置参数接口删不掉，先降级成 N 再删；这样 finally 里不留垃圾
        if config_id is not None:
            ConfigApi.update(token, config_id, KEY, NAME, VALUE, config_type="N")
        _purge(token)


def test_delete_nonexistent_config(token):
    """删除一个不存在的 configId —— 后端 NPE 路径，code=500 且 msg 是 null。"""
    r = ConfigApi.delete(token, 99999999)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 500, f"删不存在的 configId 应该失败，实际：{body}"
    assert body["msg"] is None, f"这条 NPE 路径的 msg 是 null，实际：{body['msg']!r}"


def test_get_config_list_with_pagination(token):
    """分页有效：pageSize 限制返回条数，total 不受 pageSize 影响"""
    r = ConfigApi.get_list(token, page_size=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)
    assert len(body["rows"]) <= 1, f"pageSize=1 却返回了 {len(body['rows'])} 条"
    assert body["total"] >= len(body["rows"])

    body2 = ConfigApi.get_list(token, page_size=2).json()
    assert len(body2["rows"]) <= 2, f"pageSize=2 却返回了 {len(body2['rows'])} 条"
    assert body2["total"] == body["total"], "total 不该受 pageSize 影响"


def test_get_config_list_with_filter(token):
    """筛选：configName / configKey 都是 like 模糊匹配，configType 精确匹配"""
    _fresh(token)
    try:
        ConfigApi.add(token, KEY, NAME, VALUE)

        # configKey 是 like：用完整 key 能命中
        body = ConfigApi.get_list(token, config_key=KEY, page_size=100).json()
        assert body["code"] == 200
        assert body["total"] == 1, f"按 configKey 过滤应只返回 1 条，实际 {body['total']} 条"
        assert body["rows"][0]["configKey"] == KEY

        # configKey 用前缀也能命中（证明是 like 不是等值）
        body2 = ConfigApi.get_list(token, config_key="autotest.config", page_size=100).json()
        assert body2["total"] == 1, f"configKey 应是模糊匹配，实际 total={body2['total']}"

        # configName 同样是 like
        body3 = ConfigApi.get_list(token, config_name="autotest配置", page_size=100).json()
        assert body3["total"] == 1
        assert body3["rows"][0]["configName"] == NAME

        # configType 精确匹配：我们自己建的不传 configType，落库是 N
        body4 = ConfigApi.get_list(token, config_type="N", page_size=100).json()
        assert body4["total"] >= 1
        assert all(x["configType"] == "N" for x in body4["rows"])

        # 筛不存在的，应该返回 0
        assert ConfigApi.get_list(token, config_key="autotest_zzz_none",
                                  page_size=100).json()["total"] == 0
    finally:
        _purge(token)
