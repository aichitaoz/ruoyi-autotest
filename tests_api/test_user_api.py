"""接口测试：用户管理"""
from api.user_api import UserApi


def _get_user_id(token, username):
    """从列表里按用户名取 userId，取不到直接报错（比 next 抛 StopIteration 好定位）"""
    list_r = UserApi.get_list(token)
    rows = list_r.json()["rows"]
    hit = [u["userId"] for u in rows if u["userName"] == username]
    assert hit, f"列表里找不到用户 {username}，现有用户名：{[u['userName'] for u in rows]}"
    return hit[0]


def test_get_user_list(token):
    """查询用户列表，应该返回 total 和 rows"""
    r = UserApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert body["total"] >= 1          # 至少有 admin 这个用户
    assert isinstance(body["rows"], list)

def test_add_user(token):
    """新增用户，应该成功，且能在列表里查到"""
    r = UserApi.add(token, "autotest_api_01", "接口测试用户", "test123456")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 回查：新增后必须能在列表里找到
    list_r = UserApi.get_list(token)
    rows = list_r.json()["rows"]
    usernames = [u["userName"] for u in rows]
    assert "autotest_api_01" in usernames, f"新增后列表里找不到该用户，现有：{usernames}"

def test_update_user(token):
    """修改用户昵称，应该成功，且改后能查到新值"""
    # 1. 先建一个用户
    UserApi.add(token, "autotest_update", "改前昵称", "test123456")

    # 2. 从列表里找到它的 userId
    list_r = UserApi.get_list(token)
    rows = list_r.json()["rows"]
    target = next(u for u in rows if u["userName"] == "autotest_update")
    user_id = target["userId"]
    assert target["nickName"] == "改前昵称"

    # 3. 改昵称
    r = UserApi.update(token, user_id, "autotest_update", "改后昵称")
    assert r.status_code == 200
    assert r.json()["code"] == 200

    # 4. 回查，确认改了
    detail_r = UserApi.get_by_id(token, user_id)
    assert detail_r.json()["data"]["nickName"] == "改后昵称"


def test_get_user_by_id(token):
    """按 id 查询用户，应该返回该用户的完整信息"""
    # 1. 先建一个用户
    add_r = UserApi.add(token, "autotest_getone", "查询测试用户", "test123456")
    assert add_r.json()["code"] == 200

    # 2. 从列表拿 userId
    user_id = _get_user_id(token, "autotest_getone")

    # 3. 按 id 查
    r = UserApi.get_by_id(token, user_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"
    assert body["data"]["userId"] == user_id
    assert body["data"]["userName"] == "autotest_getone"
    assert body["data"]["nickName"] == "查询测试用户"


def test_add_duplicate_user(token):
    """重复新增同名用户，应该被拒绝"""
    # 1. 建第一个
    r1 = UserApi.add(token, "autotest_dup", "重复测试用户", "test123456")
    assert r1.json()["code"] == 200

    # 2. 再建同名，应该失败
    r2 = UserApi.add(token, "autotest_dup", "重复测试用户2", "test123456")
    assert r2.status_code == 200
    body = r2.json()
    assert body["code"] != 200, f"同名用户应该被拒绝，实际返回：{body}"
    assert "已存在" in body["msg"]

    # 3. 回查：列表里只能有一个 autotest_dup，且昵称还是第一个的
    rows = UserApi.get_list(token).json()["rows"]
    dups = [u for u in rows if u["userName"] == "autotest_dup"]
    assert len(dups) == 1, f"同名用户只应存在一条，实际 {len(dups)} 条"
    assert dups[0]["nickName"] == "重复测试用户"


def test_delete_user(token):
    """删除用户，应该成功，且列表里查不到（RuoYi 是软删除，验证必须走列表接口）"""
    # 1. 先建一个用户
    UserApi.add(token, "autotest_todelete", "待删除用户", "test123456")

    # 2. 从列表拿 userId
    user_id = _get_user_id(token, "autotest_todelete")

    # 3. 删
    r = UserApi.delete(token, user_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 4. 回查：列表里应该查不到（软删除，过滤 del_flag）
    rows = UserApi.get_list(token).json()["rows"]
    usernames = [u["userName"] for u in rows]
    assert "autotest_todelete" not in usernames, f"删除后列表里仍能查到该用户：{usernames}"


def test_get_user_list_with_pagination(token):
    """分页查询，pageSize=2 时返回条数不超过 2"""
    r = UserApi.get_list(token, page_size=2)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)
    assert len(body["rows"]) <= 2, f"pageSize=2 却返回了 {len(body['rows'])} 条"
    # total 是满足条件的总条数，不受 pageSize 影响，应不少于实际返回条数
    assert body["total"] >= len(body["rows"])
