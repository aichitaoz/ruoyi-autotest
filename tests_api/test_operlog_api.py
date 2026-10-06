"""接口测试：操作日志（只读模块）

这个模块没有增删改，所以**刻意不照抄前面模块的用例结构**：
不造数据、不写清理 fixture、data 前缀无从谈起（日志是接口自己写的）。
重点全部压在**筛选**上。

两个必须守住的红线：
1. `total` 只能用「>=N」「==0」「两次查询相等」来断言，绝不能写死数字 ——
   每调一次带 @Log 的接口，这张表就多一行，前面的用例还在往里写。
2. **绝不调 DELETE /monitor/operlog/clean**（truncate 整张表）。
"""
from api.operlog_api import OperLogApi

# 一个绝不可能存在的筛选值，用来证明「多条件是 AND」以及「筛不存在返回 0」
NOBODY = "autotest_nobody_zzz"


def _pick_sample_row(token):
    """从最新的 100 条日志里挑一行字段齐全的，作为筛选条件的真实来源。

    不硬编码 title / operName，因为日志内容是接口调用的副产物，
    换个环境、换天跑就可能不一样；从真实数据里取才稳。"""
    body = OperLogApi.get_list(token, page_size=100).json()
    rows = body["rows"]
    assert rows, "操作日志表里一条数据都没有，没法做筛选用例（先随便调几个带 @Log 的接口）"
    for row in rows:
        if row.get("title") and row.get("operName") and row.get("businessType") is not None:
            return row
    return rows[0]


def test_get_operlog_list(token):
    """列表返回标准结构 {total, rows, code, msg}，字段齐全，且按 oper_id 倒序"""
    r = OperLogApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)

    # 只读模块不造数据，所以只能断言"有数据"
    assert body["total"] >= 1, "操作日志应该至少有若干条"
    assert len(body["rows"]) >= 1

    for row in body["rows"]:
        for key in ("operId", "title", "businessType", "operName",
                    "status", "operTime", "operUrl"):
            assert key in row, f"列表行里缺字段 {key}：{row}"

    # 固定按 oper_id 倒序：最新的在最前
    ids = [x["operId"] for x in body["rows"]]
    assert ids == sorted(ids, reverse=True), f"列表应按 oper_id 倒序，实际：{ids[:10]}"


def test_get_operlog_list_filter_by_title(token):
    """只按 title 筛选：title 是 like 模糊匹配，命中的每一行 title 都得包含它"""
    sample = _pick_sample_row(token)
    title = sample["title"]

    body = OperLogApi.get_list(token, title=title, page_size=100).json()
    assert body["code"] == 200
    assert body["total"] >= 1, f"用真实存在的 title={title!r} 筛选，不该是 0 条"
    for row in body["rows"]:
        assert title in row["title"], f"title 是模糊匹配，不该出现不含 {title!r} 的行：{row['title']!r}"

    # 反向：筛一个肯定不存在的 title -> 0 条
    body2 = OperLogApi.get_list(token, title="autotest不存在的模块zzz", page_size=100).json()
    assert body2["total"] == 0

    # 双向夹逼：真实 title 的命中数应该落在 [1, 全表] 之间
    all_total = OperLogApi.get_list(token, page_size=1).json()["total"]
    assert 1 <= body["total"] <= all_total, \
        f"筛选后的 total={body['total']} 应落在 1..{all_total} 之间"


def test_get_operlog_list_filter_by_oper_name(token):
    """只按 operName 筛选：同样是 like 模糊匹配"""
    sample = _pick_sample_row(token)
    oper_name = sample["operName"]

    body = OperLogApi.get_list(token, oper_name=oper_name, page_size=100).json()
    assert body["code"] == 200
    assert body["total"] >= 1, f"用真实存在的 operName={oper_name!r} 筛选，不该是 0 条"
    for row in body["rows"]:
        assert oper_name in row["operName"]

    # 反向
    body2 = OperLogApi.get_list(token, oper_name=NOBODY, page_size=100).json()
    assert body2["total"] == 0


def test_get_operlog_list_filter_combination(token):
    """【重点】多条件组合筛选：组合是 **AND** 而不是 OR。

    做法：
    1. 从真实数据里取一行的 title + operName + businessType，
       三个条件一起筛 —— 至少能命中它自己，且返回的每一行都必须同时满足三个条件；
    2. 把其中一个条件换成绝不可能成立的值，total 应该直接掉到 0。
       如果后端是 OR 组合，这一步会返回一大堆结果，测试就会红 —— 这就把 AND 锁死了；
    3. 加一个"单调收窄"的对照：三条件的 total 不得超过单条件的 total。"""
    sample = _pick_sample_row(token)
    title = sample["title"]
    oper_name = sample["operName"]
    business_type = sample["businessType"]

    # 1. 三条件组合
    combo = OperLogApi.get_list(token, title=title, oper_name=oper_name,
                                business_type=business_type, page_size=100).json()
    assert combo["code"] == 200
    assert combo["total"] >= 1, (
        f"这三条件取自真实的一行（title={title!r}, operName={oper_name!r}, "
        f"businessType={business_type}），不该是 0 条"
    )
    for row in combo["rows"]:
        assert title in row["title"], f"组合筛选漏了不匹配 title 的行：{row['title']!r}"
        assert oper_name in row["operName"], f"组合筛选漏了不匹配 operName 的行：{row['operName']!r}"
        assert row["businessType"] == business_type, \
            f"组合筛选漏了不匹配 businessType 的行：{row['businessType']}"

    # 2. AND 的证明：把一个条件换成不可能的值 -> 0
    conflict = OperLogApi.get_list(token, title=title, oper_name=NOBODY,
                                   business_type=business_type, page_size=100).json()
    assert conflict["total"] == 0, (
        f"title 命中但 operName 不可能命中，AND 组合应该是 0 条；"
        f"实际 {conflict['total']} 条 —— 说明条件之间可能被当成 OR 了"
    )

    # 3. 单调收窄：组合的 total 不该超过任一单条件的 total
    by_title = OperLogApi.get_list(token, title=title, page_size=1).json()["total"]
    by_type = OperLogApi.get_list(token, business_type=business_type, page_size=1).json()["total"]
    assert combo["total"] <= by_title, \
        f"三条件组合({combo['total']}) 不该多于单 title 条件({by_title})"
    assert combo["total"] <= by_type, \
        f"三条件组合({combo['total']}) 不该多于单 businessType 条件({by_type})"


def test_get_operlog_list_filter_by_business_type(token):
    """businessType 是整型精确匹配；businessTypes 走 SQL 的 IN 集合。

    这两个是后端两套不同的参数：单值 businessType 用 `=`，
    多值 businessTypes 用 `in (...)`。"""
    # 整型精确匹配：筛 0（其它）应该只返回 businessType == 0 的行
    body = OperLogApi.get_list(token, business_type=0, page_size=100).json()
    assert body["code"] == 200
    assert all(x["businessType"] == 0 for x in body["rows"]), \
        "businessType=0 应精确匹配，不该混进别的类型"

    # IN 集合：把上面查到的几个真实类型组合起来，total 不该少于单类型
    types = sorted({x["businessType"] for x in
                    OperLogApi.get_list(token, page_size=100).json()["rows"]})
    assert types, "日志里应该有若干 businessType"

    if len(types) >= 2:
        pair = types[:2]
        single_totals = [
            OperLogApi.get_list(token, business_type=t, page_size=1).json()["total"]
            for t in pair
        ]
        multi = OperLogApi.get_list(token, business_types=pair, page_size=100).json()
        assert multi["total"] >= max(single_totals), (
            f"businessTypes IN 集合({pair}) 的 total={multi['total']} "
            f"不该少于其中单类型的最大值 {max(single_totals)}"
        )
        for row in multi["rows"]:
            assert row["businessType"] in pair, \
                f"IN 集合筛选漏了集合外的类型：{row['businessType']}"


def test_get_operlog_list_filter_by_status(token):
    """status 是整型精确匹配（0正常 / 1异常）。用真实存在的 status 值来验，避免空表假绿。"""
    sample = _pick_sample_row(token)
    real_status = sample["status"]
    assert real_status in (0, 1), f"status 只该是 0/1，实际 {real_status!r}"

    body = OperLogApi.get_list(token, status=real_status, page_size=100).json()
    assert body["code"] == 200
    assert body["total"] >= 1, f"用真实存在的 status={real_status} 筛选，不该是 0 条"
    for row in body["rows"]:
        assert row["status"] == real_status


def test_get_operlog_list_filter_by_time_range(token):
    """时间范围筛选走 params[beginTime] / params[endTime]，按 oper_time 过滤。

    两端都用极端值来验，不需要知道具体日志时间：
    - beginTime 定在 2000 年 -> 全表都在范围内，total 应与不加条件时相同；
    - beginTime 定在 2099 年 -> 一条都不在范围内，total 应为 0。"""
    baseline = OperLogApi.get_list(token, page_size=1).json()["total"]
    assert baseline >= 1, "操作日志表不该是空的"

    # 下限设在 2000 年：全部命中
    past = OperLogApi.get_list(token, begin_time="2000-01-01 00:00:00", page_size=1).json()
    assert past["code"] == 200
    assert past["total"] == baseline, \
        f"beginTime=2000 应命中全部 {baseline} 条，实际 {past['total']} 条"

    # 下限设在 2099 年：全部落空
    future = OperLogApi.get_list(token, begin_time="2099-01-01 00:00:00", page_size=1).json()
    assert future["total"] == 0, f"beginTime=2099 应该是 0 条，实际 {future['total']} 条"

    # 上下限都设成 2099 年：同样是 0
    both = OperLogApi.get_list(token, begin_time="2099-01-01 00:00:00",
                               end_time="2099-12-31 23:59:59", page_size=1).json()
    assert both["total"] == 0

    # 时间范围 + 业务条件组合，依然生效（且不超过单条件）
    by_type = OperLogApi.get_list(token, business_type=0, page_size=1).json()["total"]
    combo = OperLogApi.get_list(token, business_type=0,
                                begin_time="2000-01-01 00:00:00", page_size=1).json()
    assert combo["total"] == by_type, \
        f"加一个覆盖全部的时间下限不该改变结果：{combo['total']} vs {by_type}"


def test_get_operlog_list_filter_nonexistent_returns_zero(token):
    """各种条件筛一个必然不存在的值，都该返回 total=0（而不是报错、也不是返回全部）"""
    cases = [
        ("title", {"title": NOBODY}),
        ("operName", {"oper_name": NOBODY}),
        ("operIp", {"oper_ip": "10.99.99.99"}),
        ("businessType 不存在的类型", {"business_type": 999}),
    ]
    for tag, kwargs in cases:
        body = OperLogApi.get_list(token, page_size=100, **kwargs).json()
        assert body["code"] == 200, f"[{tag}] 筛不存在不该报错：{body}"
        assert body["total"] == 0, f"[{tag}] 筛不存在应返回 0 条，实际 {body['total']} 条"
        assert body["rows"] == [], f"[{tag}] total=0 时 rows 也该是空，实际 {body['rows'][:2]}"


def test_get_operlog_list_with_pagination(token):
    """分页有效：pageSize 限制返回条数，total 不受 pageSize 影响"""
    assert OperLogApi.get_list(token, page_size=1).json()["total"] >= 1, \
        "操作日志表不该是空的，分页用例才有意义"

    body1 = OperLogApi.get_list(token, page_size=1).json()
    assert body1["code"] == 200
    assert "total" in body1
    assert "rows" in body1
    assert len(body1["rows"]) <= 1, f"pageSize=1 却返回了 {len(body1['rows'])} 条"
    assert body1["total"] >= len(body1["rows"])

    body3 = OperLogApi.get_list(token, page_size=3).json()
    assert len(body3["rows"]) <= 3, f"pageSize=3 却返回了 {len(body3['rows'])} 条"

    body100 = OperLogApi.get_list(token, page_size=100).json()
    assert len(body100["rows"]) <= 100

    # total 是满足条件的总数，不该随 pageSize 变化
    assert body1["total"] == body3["total"] == body100["total"], \
        f"total 不该受 pageSize 影响：{body1['total']} / {body3['total']} / {body100['total']}"

    # 分页真的在翻页：pageSize=1 拿到的那条不在 pageSize=5 的"第 4~5 条"之外
    assert len(body100["rows"]) >= len(body3["rows"])


def test_get_operlog_by_id_endpoint_not_exposed(token):
    """只读模块的边界：**没有**按 id 单查的接口。

    mapper 里有 selectOperLogById，但 controller 没有暴露；
    GET /monitor/operlog/1 会被 DELETE 那条 /{operIds} 路由匹配到，
    返回「Request method 'GET' not supported」，而不是一条日志详情。
    这条把「本模块不能照抄其他模块的 get_by_id」钉住。"""
    import requests
    from config import API_BASE_URL

    r = requests.get(
        f"{API_BASE_URL}/monitor/operlog/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 500
    assert "Request method 'GET' not supported" in body["msg"], \
        f"预期是「GET 不支持」，实际：{body}"


def test_delete_operlog_by_ids_is_noop_for_missing_ids(token):
    """删除接口确实存在，但这是**只读模块**，测试里只敢拿不存在的 id 验行为：
    service 返回 0 行 -> toAjax(0) -> code=500、msg「操作失败」，
    而且**日志条数一条都没少**（证明它是 no-op，不会误伤真实日志）。

    ⚠️ 绝不调 DELETE /monitor/operlog/clean（truncate 全表）。"""
    before = OperLogApi.get_list(token, page_size=1).json()["total"]
    assert before >= 1

    r = OperLogApi.delete_by_ids(token, 99999999)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 500, f"删不存在的 operId 应该失败，实际：{body}"
    assert body["msg"] == "操作失败"

    # 注意：这条 delete 请求本身也会被 @Log 记一行，所以 total 可能比 before 大
    # （多的是这次删除操作自己的日志），但绝不会比 before 小。
    after = OperLogApi.get_list(token, page_size=1).json()["total"]
    assert after >= before, f"删不存在的 id 不该删掉任何真实日志：{before} -> {after}"
