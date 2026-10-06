"""接口测试：岗位管理"""
from api.post_api import PostApi


def _get_post_id(token, post_code):
    """从列表里按 postCode 取 postId，取不到直接报错（比 next 抛 StopIteration 好定位）"""
    list_r = PostApi.get_list(token)
    rows = list_r.json()["rows"]
    hit = [p["postId"] for p in rows if p["postCode"] == post_code]
    assert hit, f"列表里找不到岗位 {post_code}，现有 postCode：{[p['postCode'] for p in rows]}"
    return hit[0]


def test_get_post_list(token):
    """查询岗位列表，应该返回 total 和 rows"""
    r = PostApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "查询成功"
    assert "total" in body
    assert "rows" in body
    assert body["total"] >= 1          # 至少有 ceo / se / hr / user 这几个内置岗位
    assert isinstance(body["rows"], list)
    # 每个岗位必须有 postId / postCode / postName / postSort
    for row in body["rows"]:
        assert "postId" in row
        assert "postCode" in row
        assert "postName" in row
        assert "postSort" in row


def test_add_post(token):
    """新增岗位，应该成功，且能在列表里查到"""
    r = PostApi.add(token, "autotest_post_01", "autotest岗位01", post_sort=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 回查：新增后必须能在列表里找到
    list_r = PostApi.get_list(token)
    rows = list_r.json()["rows"]
    codes = [p["postCode"] for p in rows]
    assert "autotest_post_01" in codes, f"新增后列表里找不到该岗位，现有：{codes}"


def test_get_post_by_id(token):
    """按 id 查询岗位，应该返回该岗位的完整信息"""
    # 1. 先建一个岗位
    add_r = PostApi.add(token, "autotest_post_getone", "autotest岗位查详情", post_sort=1)
    assert add_r.json()["code"] == 200

    # 2. 从列表拿 postId
    post_id = _get_post_id(token, "autotest_post_getone")

    # 3. 按 id 查
    r = PostApi.get_by_id(token, post_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"
    assert body["data"]["postId"] == post_id
    assert body["data"]["postCode"] == "autotest_post_getone"
    assert body["data"]["postName"] == "autotest岗位查详情"
    assert body["data"]["postSort"] == 1
    assert body["data"]["status"] == "0"


def test_update_post(token):
    """修改岗位名和排序，应该成功，且改后能查到新值"""
    # 1. 先建一个岗位
    PostApi.add(token, "autotest_post_update", "autotest岗位改前", post_sort=1)

    # 2. 从列表里找到它的 postId
    post_id = _get_post_id(token, "autotest_post_update")

    # 3. 改岗位名和排序
    r = PostApi.update(token, post_id, "autotest_post_update", "autotest岗位改后", post_sort=9)
    assert r.status_code == 200
    assert r.json()["code"] == 200
    assert r.json()["msg"] == "操作成功"

    # 4. 回查，确认改了
    detail_r = PostApi.get_by_id(token, post_id)
    assert detail_r.json()["data"]["postName"] == "autotest岗位改后"
    assert detail_r.json()["data"]["postSort"] == 9


def test_delete_post(token):
    """删除岗位，应该成功，且列表里查不到。
    岗位删除是物理删除（sys_post 没有 del_flag 列），这里仍按规矩走列表接口验证"""
    # 1. 先建一个岗位
    PostApi.add(token, "autotest_post_todelete", "autotest岗位待删")

    # 2. 从列表拿 postId
    post_id = _get_post_id(token, "autotest_post_todelete")

    # 3. 删
    r = PostApi.delete(token, post_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 4. 回查：列表里应该查不到
    rows = PostApi.get_list(token).json()["rows"]
    codes = [p["postCode"] for p in rows]
    assert "autotest_post_todelete" not in codes, f"删除后列表里仍能查到该岗位：{codes}"

    # 5. 岗位是物理删除，按 id 单查也不会再有 data 字段
    detail_r = PostApi.get_by_id(token, post_id)
    assert detail_r.json()["code"] == 200
    assert "data" not in detail_r.json(), f"岗位是物理删除，单查不该再有 data：{detail_r.json()}"


def test_add_duplicate_post_code(token):
    """重复新增同 postCode 的岗位，应该被拒绝"""
    # 1. 建第一个
    r1 = PostApi.add(token, "autotest_post_dupcode", "autotest岗位重复编码")
    assert r1.json()["code"] == 200

    # 2. 再建同 postCode，应该失败
    r2 = PostApi.add(token, "autotest_post_dupcode", "autotest岗位重复编码2", post_sort=2)
    assert r2.status_code == 200
    body = r2.json()
    assert body["code"] != 200, f"重复 postCode 应该被拒绝，实际返回：{body}"
    assert "岗位编码已存在" in body["msg"]

    # 3. 回查：列表里只能有一个 autotest_post_dupcode
    rows = PostApi.get_list(token).json()["rows"]
    dups = [p for p in rows if p["postCode"] == "autotest_post_dupcode"]
    assert len(dups) == 1, f"同 postCode 只应存在一条，实际 {len(dups)} 条"


def test_add_duplicate_post_name(token):
    """重复新增同 postName 的岗位，应该被拒绝（岗位名称同样唯一）"""
    # 1. 建第一个
    r1 = PostApi.add(token, "autotest_post_dupname_a", "autotest岗位重名")
    assert r1.json()["code"] == 200

    # 2. 换个 postCode 但用同名岗位，应该失败
    r2 = PostApi.add(token, "autotest_post_dupname_b", "autotest岗位重名", post_sort=2)
    assert r2.status_code == 200
    body = r2.json()
    assert body["code"] != 200, f"重复岗位名应该被拒绝，实际返回：{body}"
    assert "岗位名称已存在" in body["msg"]

    # 3. 回查：列表里只能有一个叫 autotest岗位重名 的岗位
    rows = PostApi.get_list(token).json()["rows"]
    dups = [p for p in rows if p["postName"] == "autotest岗位重名"]
    assert len(dups) == 1, f"同名岗位只应存在一条，实际 {len(dups)} 条"


def test_add_post_without_required_fields(token):
    """新增岗位缺必填字段，应该被拒绝并给出对应中文提示"""
    # 1. 不给 postCode
    r1 = PostApi.add(token, "", "autotest岗位无编码", post_sort=1)
    assert r1.status_code == 200
    assert r1.json()["code"] == 500
    assert r1.json()["msg"] == "岗位编码不能为空"

    # 2. 不给 postName
    r2 = PostApi.add(token, "autotest_post_noname", "", post_sort=1)
    assert r2.status_code == 200
    assert r2.json()["code"] == 500
    assert r2.json()["msg"] == "岗位名称不能为空"

    # 3. 不给 postSort（传空值模拟未填）
    r3 = PostApi.add(token, "autotest_post_nosort", "autotest岗位无排序", post_sort=None)
    assert r3.status_code == 200
    assert r3.json()["code"] == 500
    assert r3.json()["msg"] == "显示顺序不能为空"

    # 4. 回查：这三个失败的新增都不该落库
    rows = PostApi.get_list(token).json()["rows"]
    codes = [p["postCode"] for p in rows]
    names = [p["postName"] for p in rows]
    assert "autotest_post_noname" not in codes, f"校验失败的岗位却落库了，现有：{codes}"
    assert "autotest岗位无排序" not in names, f"校验失败的岗位却落库了，现有：{names}"


def test_get_post_list_with_pagination(token):
    """分页查询，pageSize=1 时返回条数不超过 1"""
    r = PostApi.get_list(token, page_size=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)
    assert len(body["rows"]) <= 1, f"pageSize=1 却返回了 {len(body['rows'])} 条"
    # total 是满足条件的总条数，不受 pageSize 影响，应不少于实际返回条数
    assert body["total"] >= len(body["rows"])