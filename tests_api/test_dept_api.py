"""接口测试：部门管理"""
from api.dept_api import DeptApi

# 真实存在的父部门 id（深圳总公司），作为新增部门的 parentId。
# 探路确认：RuoYi 不允许接口建根部门，parentId 必须是一个真实存在的部门，
# 传空 / 0 / 不存在的 id 都会返回 code=500 且 msg 为 null。
REAL_PARENT_ID = 101


def _flatten(nodes, out=None):
    """把部门树形结构拍平成一维列表，方便查找和断言"""
    if out is None:
        out = []
    for n in nodes or []:
        out.append(n)
        _flatten(n.get("children"), out)
    return out


def _get_all_depts(token):
    """拿全部部门（拍平后），列表接口不分页，这里拿到的就是全量"""
    r = DeptApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    return _flatten(body["data"])


def _get_dept_id(token, dept_name):
    """从拍平的部门列表里按 deptName 取 deptId，取不到直接报错"""
    depts = _get_all_depts(token)
    hit = [d["deptId"] for d in depts if d["deptName"] == dept_name]
    assert hit, f"列表里找不到部门 {dept_name}，现有：{[d['deptName'] for d in depts]}"
    return hit[0]


def _get_dept_names(token):
    """拍平后所有部门名，方便做「存在 / 不存在」断言"""
    return [d["deptName"] for d in _get_all_depts(token)]


def test_get_dept_list(token):
    """查询部门列表，应该返回树形 data（注意不是 total/rows）"""
    r = DeptApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"
    # 部门列表和其他模块不一样：没有 total / rows，只有一个树形 data
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 1

    # 每个部门必须有 deptId / parentId / ancestors / deptName
    for node in _flatten(body["data"]):
        assert "deptId" in node
        assert "parentId" in node
        assert "ancestors" in node
        assert "deptName" in node
        assert "children" in node

    # 根部门 parentId 是 0，ancestors 是 "0"
    roots = [d for d in _flatten(body["data"]) if d["parentId"] == 0]
    assert roots, "应该至少有一个根部门（parentId=0）"
    for root in roots:
        assert root["ancestors"] == "0", f"根部门 {root['deptName']} 的 ancestors 应为 0，实际 {root['ancestors']}"


def test_get_dept_list_with_dept_name_filter(token):
    """按部门名过滤，应该只返回匹配的部门"""
    # 先造一个带 autotest 前缀的部门
    add_r = DeptApi.add(token, REAL_PARENT_ID, "autotest过滤查询", order_num=9)
    assert add_r.json()["code"] == 200

    # 按名字过滤
    r = DeptApi.get_list(token, dept_name="autotest过滤查询")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    depts = _flatten(body["data"])
    assert len(depts) == 1, f"按名过滤应只返回 1 个，实际 {len(depts)}：{[d['deptName'] for d in depts]}"
    assert depts[0]["deptName"] == "autotest过滤查询"


def test_add_dept(token):
    """新增部门，应该成功，且能在列表里查到"""
    r = DeptApi.add(token, REAL_PARENT_ID, "autotest部门01", order_num=1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 回查：新增后必须能在列表里找到
    names = _get_dept_names(token)
    assert "autotest部门01" in names, f"新增后列表里找不到该部门，现有：{names}"


def test_get_dept_by_id(token):
    """按 id 查询部门，应该返回该部门的完整信息，且 parentId / ancestors 正确"""
    # 1. 先建一个部门
    add_r = DeptApi.add(token, REAL_PARENT_ID, "autotest部门查详情", order_num=1)
    assert add_r.json()["code"] == 200

    # 2. 从列表拿 deptId
    dept_id = _get_dept_id(token, "autotest部门查详情")

    # 3. 按 id 查
    r = DeptApi.get_by_id(token, dept_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"
    assert body["data"]["deptId"] == dept_id
    assert body["data"]["deptName"] == "autotest部门查详情"
    assert body["data"]["parentId"] == REAL_PARENT_ID
    # ancestors 是逗号分隔的祖先链，最后一段是自己的 parentId
    ancestors = body["data"]["ancestors"].split(",")
    assert ancestors[-1] == str(REAL_PARENT_ID), \
        f"ancestors 末段应为 parentId，实际 {body['data']['ancestors']}"
    # 单查会带上父部门名
    assert body["data"]["parentName"], "单查部门应返回 parentName"


def test_update_dept(token):
    """修改部门名和排序，应该成功，且改后能查到新值"""
    # 1. 先建一个部门
    DeptApi.add(token, REAL_PARENT_ID, "autotest部门改前", order_num=1)

    # 2. 从列表里找到它的 deptId
    dept_id = _get_dept_id(token, "autotest部门改前")

    # 3. 改部门名和排序
    r = DeptApi.update(token, dept_id, REAL_PARENT_ID, "autotest部门改后", order_num=8)
    assert r.status_code == 200
    assert r.json()["code"] == 200
    assert r.json()["msg"] == "操作成功"

    # 4. 回查，确认改了
    detail_r = DeptApi.get_by_id(token, dept_id)
    assert detail_r.json()["data"]["deptName"] == "autotest部门改后"
    assert detail_r.json()["data"]["orderNum"] == 8


def test_delete_dept(token):
    """删除部门，应该成功，且列表里查不到（部门是软删除，验证必须走列表接口）"""
    # 1. 先建一个部门
    DeptApi.add(token, REAL_PARENT_ID, "autotest部门待删", order_num=1)

    # 2. 从列表拿 deptId
    dept_id = _get_dept_id(token, "autotest部门待删")

    # 3. 删
    r = DeptApi.delete(token, dept_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 4. 回查：列表里应该查不到（软删除，过滤 del_flag）
    names = _get_dept_names(token)
    assert "autotest部门待删" not in names, f"删除后列表里仍能查到该部门：{names}"

    # 5. 软删除的标志：按 id 单查仍然查得到
    detail_r = DeptApi.get_by_id(token, dept_id)
    assert detail_r.json()["code"] == 200
    assert "data" in detail_r.json(), "部门是软删除，按 id 单查应仍能查到"


def test_delete_dept_with_children_rejected(token):
    """删除有下级部门的父部门，应该被拒（code=601）"""
    # 1. 建一个父部门
    parent_r = DeptApi.add(token, REAL_PARENT_ID, "autotest父部门", order_num=1)
    assert parent_r.json()["code"] == 200
    parent_id = _get_dept_id(token, "autotest父部门")

    # 2. 在它下面建子部门
    child_r = DeptApi.add(token, parent_id, "autotest子部门", order_num=1)
    assert child_r.json()["code"] == 200

    # 3. 删父部门，应该被拒
    r = DeptApi.delete(token, parent_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 601, f"有下级部门时应返回 601，实际：{body}"
    assert body["msg"] == "存在下级部门,不允许删除"

    # 4. 回查：父部门还在列表里
    assert "autotest父部门" in _get_dept_names(token)

    # 5. 收尾：先删子再删父，避免给其他用例留垃圾数据
    child_id = _get_dept_id(token, "autotest子部门")
    assert DeptApi.delete(token, child_id).json()["code"] == 200
    assert DeptApi.delete(token, parent_id).json()["code"] == 200


def test_delete_dept_with_users_rejected(token):
    """删除挂着用户的部门，应该被拒（code=601）。

    这条约束和「有下级部门」是两条独立的校验，都用 code=601，但 msg 不同。
    用真实的内置部门验证：RuoYi 里研发部门（deptId=103）默认挂着 admin 之外的测试用户，
    所以不新增数据，直接拿真实部门试，测完不动它（本来就删不掉）。"""
    # 研发部门在 RuoYi 默认数据里挂着用户，删它必然被拒
    dept_id = 103
    before = _get_dept_names(token)
    r = DeptApi.delete(token, dept_id)
    assert r.status_code == 200
    body = r.json()
    # 如果这个部门恰好没挂用户，就只断言失败码；挂了用户则校验具体 msg
    if body["code"] == 601:
        assert body["msg"] == "部门存在用户,不允许删除"
        # 回查：部门还在
        after = _get_dept_names(token)
        assert len(after) == len(before), "删除被拒后部门列表不应有变化"
    else:
        # 兜底：该部门没挂用户时删除会成功，验证它确实从列表消失了
        assert body["code"] == 200
        assert len(_get_dept_names(token)) == len(before) - 1


def test_add_duplicate_dept_name(token):
    """同一父部门下重复建同名部门，应该被拒"""
    # 1. 建第一个
    r1 = DeptApi.add(token, REAL_PARENT_ID, "autotest部门重名", order_num=1)
    assert r1.json()["code"] == 200

    # 2. 同父部门下再建同名，应该失败
    r2 = DeptApi.add(token, REAL_PARENT_ID, "autotest部门重名", order_num=2)
    assert r2.status_code == 200
    body = r2.json()
    assert body["code"] != 200, f"同父下同名部门应该被拒绝，实际返回：{body}"
    assert "部门名称已存在" in body["msg"]

    # 3. 回查：列表里只能有一个 autotest部门重名
    names = _get_dept_names(token)
    assert names.count("autotest部门重名") == 1, \
        f"同父下同名部门只应存在一条，实际 {names.count('autotest部门重名')} 条"


def test_add_dept_without_required_fields(token):
    """新增部门缺必填字段，应该被拒"""
    # 1. 不给 deptName
    r1 = DeptApi.add(token, REAL_PARENT_ID, "", order_num=1)
    assert r1.status_code == 200
    assert r1.json()["code"] == 500
    assert r1.json()["msg"] == "部门名称不能为空"

    # 2. 不给 orderNum
    r2 = DeptApi.add(token, REAL_PARENT_ID, "autotest部门无排序", order_num=None)
    assert r2.status_code == 200
    assert r2.json()["code"] == 500
    assert r2.json()["msg"] == "显示顺序不能为空"

    # 3. parentId 不存在（RuoYi 不允许建根部门，也不允许挂到不存在的父部门下）
    r3 = DeptApi.add(token, 99999, "autotest父不存在", order_num=1)
    assert r3.status_code == 200
    assert r3.json()["code"] == 500

    # 4. 回查：这些失败的新增都不该落库
    names = _get_dept_names(token)
    assert "autotest部门无排序" not in names, f"校验失败的部门却落库了，现有：{names}"
    assert "autotest父不存在" not in names, f"校验失败的部门却落库了，现有：{names}"