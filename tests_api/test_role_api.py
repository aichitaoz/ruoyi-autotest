"""接口测试：角色管理"""
from api.role_api import RoleApi


def _get_role_id(token, role_key):
    """从列表里按 roleKey 取 roleId，取不到直接报错（比 next 抛 StopIteration 好定位）"""
    list_r = RoleApi.get_list(token)
    rows = list_r.json()["rows"]
    hit = [r["roleId"] for r in rows if r["roleKey"] == role_key]
    assert hit, f"列表里找不到角色 {role_key}，现有 roleKey：{[r['roleKey'] for r in rows]}"
    return hit[0]


def test_get_role_list(token):
    """查询角色列表，应该返回 total 和 rows"""
    r = RoleApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "查询成功"
    assert "total" in body
    assert "rows" in body
    assert body["total"] >= 1          # 至少有 admin / common 这两个内置角色
    assert isinstance(body["rows"], list)
    # 每个角色必须有 roleId / roleName / roleKey
    for row in body["rows"]:
        assert "roleId" in row
        assert "roleName" in row
        assert "roleKey" in row


def test_add_role(token):
    """新增角色，应该成功，且能在列表里查到"""
    r = RoleApi.add(token, "autotest角色01", "autotest_role_01", role_sort=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 回查：新增后必须能在列表里找到
    list_r = RoleApi.get_list(token)
    rows = list_r.json()["rows"]
    role_keys = [x["roleKey"] for x in rows]
    assert "autotest_role_01" in role_keys, f"新增后列表里找不到该角色，现有：{role_keys}"


def test_get_role_by_id(token):
    """按 id 查询角色，应该返回该角色的完整信息"""
    # 1. 先建一个角色
    add_r = RoleApi.add(token, "autotest角色查详情", "autotest_role_getone")
    assert add_r.json()["code"] == 200

    # 2. 从列表拿 roleId
    role_id = _get_role_id(token, "autotest_role_getone")

    # 3. 按 id 查
    r = RoleApi.get_by_id(token, role_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"
    assert body["data"]["roleId"] == role_id
    assert body["data"]["roleName"] == "autotest角色查详情"
    assert body["data"]["roleKey"] == "autotest_role_getone"
    # admin 标记：新建角色不是超级管理员角色
    assert body["data"]["admin"] is False


def test_update_role(token):
    """修改角色名，应该成功，且改后能查到新值"""
    # 1. 先建一个角色
    RoleApi.add(token, "autotest角色改前", "autotest_role_update", role_sort=1)

    # 2. 从列表里找到它的 roleId
    role_id = _get_role_id(token, "autotest_role_update")

    # 3. 改角色名
    r = RoleApi.update(token, role_id, "autotest角色改后", "autotest_role_update", role_sort=5)
    assert r.status_code == 200
    assert r.json()["code"] == 200
    assert r.json()["msg"] == "操作成功"

    # 4. 回查，确认改了
    detail_r = RoleApi.get_by_id(token, role_id)
    assert detail_r.json()["data"]["roleName"] == "autotest角色改后"
    assert detail_r.json()["data"]["roleSort"] == 5


def test_delete_role(token):
    """删除角色，应该成功，且列表里查不到（RuoYi 是软删除，验证必须走列表接口）"""
    # 1. 先建一个角色
    RoleApi.add(token, "autotest角色待删", "autotest_role_todelete")

    # 2. 从列表拿 roleId
    role_id = _get_role_id(token, "autotest_role_todelete")

    # 3. 删
    r = RoleApi.delete(token, role_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 4. 回查：列表里应该查不到（软删除，过滤 del_flag）
    rows = RoleApi.get_list(token).json()["rows"]
    role_keys = [x["roleKey"] for x in rows]
    assert "autotest_role_todelete" not in role_keys, f"删除后列表里仍能查到该角色：{role_keys}"


def test_add_duplicate_role_key(token):
    """重复新增同 roleKey 的角色，应该被拒绝"""
    # 1. 建第一个
    r1 = RoleApi.add(token, "autotest角色重复", "autotest_role_dup")
    assert r1.json()["code"] == 200

    # 2. 再建同 roleKey，应该失败
    r2 = RoleApi.add(token, "autotest角色重复2", "autotest_role_dup")
    assert r2.status_code == 200
    body = r2.json()
    assert body["code"] != 200, f"重复 roleKey 应该被拒绝，实际返回：{body}"
    assert "已存在" in body["msg"]

    # 3. 回查：列表里只能有一个 autotest_role_dup
    rows = RoleApi.get_list(token).json()["rows"]
    dups = [x for x in rows if x["roleKey"] == "autotest_role_dup"]
    assert len(dups) == 1, f"同 roleKey 只应存在一条，实际 {len(dups)} 条"


def test_add_role_without_role_key(token):
    """新增角色不传 roleKey，应该被拒绝（权限字符不能为空）"""
    # add 封装里 role_key 是必填位置参数，这里显式传空串模拟不填
    r = RoleApi.add(token, "autotest角色无权限字符", "", role_sort=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] != 200, f"缺少 roleKey 应该被拒绝，实际返回：{body}"
    assert body["msg"] == "权限字符不能为空"

    # 回查：列表里不应该出现这个角色名
    rows = RoleApi.get_list(token).json()["rows"]
    names = [x["roleName"] for x in rows]
    assert "autotest角色无权限字符" not in names, f"新增失败却落库了，现有：{names}"


def test_get_role_list_with_pagination(token):
    """分页查询，pageSize=1 时返回条数不超过 1"""
    r = RoleApi.get_list(token, page_size=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert "total" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)
    assert len(body["rows"]) <= 1, f"pageSize=1 却返回了 {len(body['rows'])} 条"
    # total 是满足条件的总条数，不受 pageSize 影响，应不少于实际返回条数
    assert body["total"] >= len(body["rows"])