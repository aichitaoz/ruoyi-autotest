"""接口测试：通知公告"""
import requests

from api.notice_api import NoticeApi
from config import API_BASE_URL

# 本模块的固定测试数据（前缀 autotest）
TITLE = "autotest公告01"
TITLE_PREFIX = "autotest"

# 必填校验的报错文案（实体 SysNotice 上的 @NotBlank / @Xss / @Size）
MSG_NO_TITLE = "公告标题不能为空"
MSG_XSS = "公告标题不能包含脚本字符"
MSG_TOO_LONG = "公告标题不能超过50个字符"


def _purge(token):
    """用例内收尾：删掉所有 autotest 前缀的通知公告。

    为什么必须在用例里清、不能只靠 conftest 的「跑前清」：
    跑前清救不了「跑完到下次开跑之间」这段窗口（2026-10-06 菜单模块白屏的教训）。
    """
    rows = NoticeApi.get_list(token, notice_title=TITLE_PREFIX, page_size=100).json()["rows"]
    for row in rows:
        NoticeApi.delete(token, row["noticeId"])


def _fresh(token):
    """清干净，保证用例起点是确定的"""
    _purge(token)
    left = NoticeApi.get_list(token, notice_title=TITLE_PREFIX, page_size=100).json()["total"]
    assert left == 0, f"前置清理没干净，还剩 {left} 条 autotest 公告"


def _get_notice_id(token, notice_title):
    """从列表里按 noticeTitle 取 noticeId，取不到直接报错"""
    rows = NoticeApi.get_list(token, notice_title=notice_title, page_size=100).json()["rows"]
    hit = [r["noticeId"] for r in rows if r["noticeTitle"] == notice_title]
    assert hit, (f"列表里找不到 noticeTitle={notice_title}，"
                 f"现有：{[r['noticeTitle'] for r in rows]}")
    return hit[0]


def test_get_notice_list(token):
    """列表返回标准结构 {total, rows, code, msg}，每行含必要字段"""
    r = NoticeApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)
    assert body["total"] >= 1

    for row in body["rows"]:
        for key in ("noticeId", "noticeTitle", "noticeType", "status"):
            assert key in row, f"列表行里缺字段 {key}：{row}"
        # notice_content 是 longblob，SQL 里 cast 成 char 返回，字段必须在
        assert "noticeContent" in row


def test_add_notice(token):
    """新增通知公告，应该成功，且能在列表里查到"""
    _fresh(token)
    try:
        r = NoticeApi.add(token, TITLE, notice_type="1", notice_content="autotest公告内容")
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["msg"] == "操作成功"

        # 回查：新增后必须能在列表里找到
        rows = NoticeApi.get_list(token, notice_title=TITLE, page_size=100).json()["rows"]
        hit = [x for x in rows if x["noticeTitle"] == TITLE]
        assert len(hit) == 1, f"新增后应恰有 1 条 {TITLE}，实际 {len(hit)} 条"
        assert hit[0]["noticeType"] == "1"
        assert hit[0]["status"] == "0"
    finally:
        _purge(token)


def test_get_notice_by_id(token):
    """按 id 查询单条通知公告，应该返回该条完整信息"""
    _fresh(token)
    try:
        assert NoticeApi.add(token, TITLE, notice_type="2",
                             notice_content="autotest查详情内容").json()["code"] == 200
        notice_id = _get_notice_id(token, TITLE)

        r = NoticeApi.get_by_id(token, notice_id)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["msg"] == "操作成功"
        assert body["data"]["noticeId"] == notice_id
        assert body["data"]["noticeTitle"] == TITLE
        assert body["data"]["noticeType"] == "2"
        assert body["data"]["noticeContent"] == "autotest查详情内容"
        assert body["data"]["status"] == "0"
    finally:
        _purge(token)


def test_update_notice(token):
    """修改公告标题、类型、内容和状态，应该成功，且改后能查到新值"""
    _fresh(token)
    try:
        NoticeApi.add(token, "autotest公告改前", notice_type="1", notice_content="改前内容")
        notice_id = _get_notice_id(token, "autotest公告改前")

        r = NoticeApi.update(token, notice_id, "autotest公告改后", notice_type="2",
                             notice_content="改后内容", status="1")
        assert r.status_code == 200
        assert r.json()["code"] == 200
        assert r.json()["msg"] == "操作成功"

        # 回查，确认都改了
        data = NoticeApi.get_by_id(token, notice_id).json()["data"]
        assert data["noticeTitle"] == "autotest公告改后"
        assert data["noticeType"] == "2"
        assert data["noticeContent"] == "改后内容"
        assert data["status"] == "1"
    finally:
        _purge(token)


def test_delete_notice(token):
    """删除通知公告，应该成功，且列表里查不到（物理删除，验证必须走列表接口）"""
    _fresh(token)
    try:
        NoticeApi.add(token, TITLE, notice_type="1")
        notice_id = _get_notice_id(token, TITLE)

        r = NoticeApi.delete(token, notice_id)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["msg"] == "操作成功"

        # 老规矩：删除验证走列表接口
        rows = NoticeApi.get_list(token, notice_title=TITLE_PREFIX, page_size=100).json()["rows"]
        assert notice_id not in [x["noticeId"] for x in rows], "删除后列表里仍能查到"

        # 物理删除的标志：按 id 单查也不会再有 data 字段
        detail = NoticeApi.get_by_id(token, notice_id).json()
        assert detail["code"] == 200
        assert "data" not in detail, f"通知公告是物理删除，单查不该再有 data：{detail}"
    finally:
        _purge(token)


def test_add_notice_without_required_fields(token):
    """缺公告标题应该被拒；notice_title 空串和整个不传的文案都是「公告标题不能为空」。"""
    _fresh(token)
    try:
        # 不传 noticeTitle
        r1 = requests.post(
            f"{API_BASE_URL}/system/notice",
            headers={"Authorization": f"Bearer {token}"},
            json={"noticeType": "1"},
        )
        assert r1.status_code == 200
        assert r1.json()["code"] == 500
        assert r1.json()["msg"] == MSG_NO_TITLE

        # noticeTitle 传空串
        r2 = NoticeApi.add(token, "", notice_type="1")
        assert r2.status_code == 200
        assert r2.json()["code"] == 500
        assert r2.json()["msg"] == MSG_NO_TITLE

        # 完全空 body
        r3 = requests.post(
            f"{API_BASE_URL}/system/notice",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert r3.status_code == 200
        assert r3.json()["code"] == 500
        assert r3.json()["msg"] == MSG_NO_TITLE

        # 回查：这些失败的新增都不该落库
        assert NoticeApi.get_list(token, notice_title=TITLE_PREFIX,
                                  page_size=100).json()["total"] == 0
    finally:
        _purge(token)


def test_add_notice_requires_notice_type(token):
    """【实体校验与 DB 约束不一致的坑】只传 noticeTitle、不传 noticeType 会**建失败**。

    SysNotice 实体上只有 noticeTitle 标了 @NotBlank，noticeType 没标必填，
    看着像是可以省略；但 DB 里 notice_type 是 **NOT NULL 且没有默认值**，
    而 insertNotice 的 XML 又是"字段非空才拼进 SQL"，
    于是 SQL 就变成了不含 notice_type 的 insert -> 直接抛
    「Field 'notice_type' doesn't have a default value」。

    结论：**建通知公告必须带 noticeType**，这条依赖只能靠调用方自觉（实体注解没兜住）。
    这里把行为如实锁住，并附上反向对照（带了 noticeType 就能建成功）。"""
    _fresh(token)
    try:
        # 只传 noticeTitle -> 500，且报错里能看到是 notice_type 的问题
        r = requests.post(
            f"{API_BASE_URL}/system/notice",
            headers={"Authorization": f"Bearer {token}"},
            json={"noticeTitle": TITLE},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 500, f"不传 noticeType 应该建失败，实际：{body}"
        assert "notice_type" in body["msg"], f"报错应指向 notice_type，实际：{body['msg'][:200]!r}"
        assert "doesn't have a default value" in body["msg"]

        # 回查：确实没落库
        assert NoticeApi.get_list(token, notice_title=TITLE,
                                  page_size=100).json()["total"] == 0

        # 反向对照：带上 noticeType 就能建成功
        ok = NoticeApi.add(token, TITLE, notice_type="1")
        assert ok.json()["code"] == 200, f"带上 noticeType 应能建成功，实际：{ok.json()}"
        assert NoticeApi.get_list(token, notice_title=TITLE, page_size=100).json()["total"] == 1
    finally:
        _purge(token)


def test_add_notice_duplicate_title_allowed(token):
    """反向锁：noticeTitle **不唯一**。表上没有唯一索引、后端也不查重，
    所以重复标题会老老实实落两条（和字典类型/参数配置的唯一约束形成对照）。"""
    _fresh(token)
    try:
        r1 = NoticeApi.add(token, "autotest重复标题", notice_type="1", notice_content="A")
        assert r1.json()["code"] == 200

        # 同标题、不同内容 —— 期望成功
        r2 = NoticeApi.add(token, "autotest重复标题", notice_type="2", notice_content="B")
        assert r2.status_code == 200
        assert r2.json()["code"] == 200, f"noticeTitle 不唯一，这里期望建成功，实际：{r2.json()}"

        rows = [x for x in NoticeApi.get_list(token, notice_title="autotest重复标题",
                                             page_size=100).json()["rows"]
                if x["noticeTitle"] == "autotest重复标题"]
        assert len(rows) == 2, f"同标题应能有 2 条，实际 {len(rows)} 条"
        assert {x["noticeContent"] for x in rows} == {"A", "B"}
    finally:
        _purge(token)


def test_add_notice_title_validation(token):
    """noticeTitle 比别的模块严，有两道额外校验（@Xss 和 @Size(max=50)）。

    Xss：含脚本字符会被拒；
    长度：超过 50 字会被拒（DB 列也是 varchar(50)）。
    这两条都发生在业务校验层，失败的新增不落库。"""
    _fresh(token)
    try:
        # 带脚本字符
        r1 = NoticeApi.add(token, "autotest<script>alert(1)</script>", notice_type="1")
        assert r1.status_code == 200
        assert r1.json()["code"] == 500
        assert r1.json()["msg"] == MSG_XSS

        # 超过 50 字
        r2 = NoticeApi.add(token, "autotest" + "长" * 60, notice_type="1")
        assert r2.status_code == 200
        assert r2.json()["code"] == 500
        assert r2.json()["msg"] == MSG_TOO_LONG

        # 回查：都没落库
        assert NoticeApi.get_list(token, notice_title=TITLE_PREFIX,
                                  page_size=100).json()["total"] == 0

        # 反向对照：刚好 50 字（10 个 ASCII + 40 个汉字）应能建成功
        ok_title = "autotest" + "长" * 40
        assert len(ok_title) == 48
        ok = NoticeApi.add(token, ok_title, notice_type="1")
        assert ok.json()["code"] == 200, f"未超长应能建成功，实际：{ok.json()}"
    finally:
        _purge(token)


def test_delete_nonexistent_notice(token):
    """删除一个不存在的 noticeId —— 报 code=500、msg「操作失败」。

    注意这和 dict_data / config 的同类场景不一样：
    那两个是后端 NPE（msg 是 null），这个只是 service 返回 0 行、
    toAjax(0) 走了 error() 分支，所以有正经的中文文案。"""
    r = NoticeApi.delete(token, 99999999)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 500, f"删不存在的 noticeId 应该失败，实际：{body}"
    assert body["msg"] == "操作失败", f"报错文案应是「操作失败」，实际：{body['msg']!r}"


def test_get_notice_list_with_pagination(token):
    """分页有效：pageSize 限制返回条数，total 不受 pageSize 影响"""
    r = NoticeApi.get_list(token, page_size=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)
    assert len(body["rows"]) <= 1, f"pageSize=1 却返回了 {len(body['rows'])} 条"
    assert body["total"] >= len(body["rows"])

    body2 = NoticeApi.get_list(token, page_size=2).json()
    assert len(body2["rows"]) <= 2, f"pageSize=2 却返回了 {len(body2['rows'])} 条"
    assert body2["total"] == body["total"], "total 不该受 pageSize 影响"


def test_get_notice_list_with_filter(token):
    """筛选：noticeTitle / noticeType 生效；筛不存在的返回 0。

    ⚠️ 不要用 status 做筛选验证 —— SQL 里没有 status 条件，传了会被静默忽略。"""
    _fresh(token)
    try:
        NoticeApi.add(token, "autotest公告A", notice_type="1", notice_content="c1")
        NoticeApi.add(token, "autotest公告B", notice_type="2", notice_content="c2")

        # noticeTitle 是 like 模糊匹配
        body = NoticeApi.get_list(token, notice_title=TITLE_PREFIX, page_size=100).json()
        assert body["code"] == 200
        assert body["total"] == 2, f"按 autotest 前缀过滤应返回 2 条，实际 {body['total']} 条"
        assert body["rows"][0]["noticeTitle"].startswith("autotest")

        # 用完整标题能精确命中 1 条
        body2 = NoticeApi.get_list(token, notice_title="autotest公告A", page_size=100).json()
        assert body2["total"] == 1
        assert body2["rows"][0]["noticeTitle"] == "autotest公告A"

        # noticeType 是精确匹配
        body3 = NoticeApi.get_list(token, notice_type="2", page_size=100).json()
        assert body3["total"] >= 1
        assert all(x["noticeType"] == "2" for x in body3["rows"])

        # 两个条件组合
        body4 = NoticeApi.get_list(token, notice_title=TITLE_PREFIX,
                                   notice_type="2", page_size=100).json()
        assert body4["total"] == 1, f"组合过滤应只 1 条，实际 {body4['total']} 条"
        assert body4["rows"][0]["noticeTitle"] == "autotest公告B"

        # 筛不存在的，应该返回 0
        assert NoticeApi.get_list(token, notice_title="autotest_zzz_none",
                                  page_size=100).json()["total"] == 0
    finally:
        _purge(token)
