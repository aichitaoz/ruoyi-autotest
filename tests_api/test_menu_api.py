"""接口测试：菜单管理"""
from api.menu_api import MenuApi

# 真实存在的父菜单 id（系统管理目录，menuType=M，menuId=1），
# 探路确认：菜单的 parentId 传 0 能建根菜单、传不存在的 id 也不报错，
# 但为了让测试贴近真实用法，这里统一挂在一个真实存在的目录下。
REAL_PARENT_ID = 1

# 三种菜单类型
TYPE_DIR = "M"     # 目录
TYPE_MENU = "C"    # 菜单
TYPE_BUTTON = "F"  # 按钮


def _flatten(nodes, out=None):
    """把菜单列表拍平。菜单接口现在返回的是平铺数组（children 全为空），
    这里保留递归是为了以后后端改成树形返回也不用改用例。"""
    if out is None:
        out = []
    for n in nodes or []:
        out.append(n)
        _flatten(n.get("children"), out)
    return out


def _get_all_menus(token):
    """拿全部菜单（拍平后）。菜单接口不分页，拿到的就是全量"""
    r = MenuApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    return _flatten(body["data"])


def _get_menu_id(token, menu_name):
    """从菜单列表里按 menuName 取 menuId，取不到直接报错"""
    menus = _get_all_menus(token)
    hit = [m["menuId"] for m in menus if m["menuName"] == menu_name]
    assert hit, f"列表里找不到菜单 {menu_name}"
    return hit[0]


def _get_menu_names(token):
    """所有菜单名，方便做「存在 / 不存在」断言"""
    return [m["menuName"] for m in _get_all_menus(token)]


def test_get_menu_list(token):
    """查询菜单列表，应该返回平铺的 data（注意不是 total/rows）"""
    r = MenuApi.get_list(token)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"
    # 菜单列表没有 total / rows，只有一个 data
    assert "total" not in body
    assert "rows" not in body
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 1

    # 每条菜单必须有这些字段
    for node in _flatten(body["data"]):
        assert "menuId" in node
        assert "menuName" in node
        assert "parentId" in node
        assert "menuType" in node
        assert "orderNum" in node

    # 三种类型都要有
    types = {m["menuType"] for m in _flatten(body["data"])}
    assert {"M", "C", "F"} <= types, f"系统菜单应包含 M/C/F 三种类型，实际有：{types}"

    # 根菜单 parentId 是 0
    roots = [m for m in _flatten(body["data"]) if m["parentId"] == 0]
    assert roots, "应该至少有一个根菜单（parentId=0）"


def test_add_menu_directory(token):
    """新增目录（menuType=M），应该成功，且能在列表里查到"""
    r = MenuApi.add(token, REAL_PARENT_ID, "autotest目录M", TYPE_DIR,
                    order_num=9, path="autotest_dir")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 回查：新增后必须能在列表里找到
    menus = _get_all_menus(token)
    hit = next((m for m in menus if m["menuName"] == "autotest目录M"), None)
    assert hit, f"新增后列表里找不到该目录，现有：{_get_menu_names(token)}"
    assert hit["menuType"] == TYPE_DIR
    assert hit["parentId"] == REAL_PARENT_ID
    assert hit["path"] == "autotest_dir"


def test_add_menu_menu(token):
    """新增菜单（menuType=C），应该成功，且 path / component / perms 都落库"""
    r = MenuApi.add(token, REAL_PARENT_ID, "autotest菜单C", TYPE_MENU,
                    order_num=9, path="autotest_menu",
                    component="system/autotest/index", perms="autotest:menu:list")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 回查
    menus = _get_all_menus(token)
    hit = next((m for m in menus if m["menuName"] == "autotest菜单C"), None)
    assert hit, f"新增后列表里找不到该菜单，现有：{_get_menu_names(token)}"
    assert hit["menuType"] == TYPE_MENU
    assert hit["path"] == "autotest_menu"
    assert hit["component"] == "system/autotest/index"
    assert hit["perms"] == "autotest:menu:list"


def test_add_menu_button(token):
    """新增按钮（menuType=F），应该成功。按钮只需 perms，不用 path / component"""
    r = MenuApi.add(token, REAL_PARENT_ID, "autotest按钮F", TYPE_BUTTON,
                    order_num=9, perms="autotest:button:query")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 回查
    menus = _get_all_menus(token)
    hit = next((m for m in menus if m["menuName"] == "autotest按钮F"), None)
    assert hit, f"新增后列表里找不到该按钮，现有：{_get_menu_names(token)}"
    assert hit["menuType"] == TYPE_BUTTON
    assert hit["perms"] == "autotest:button:query"


def test_get_menu_by_id(token):
    """按 id 查询菜单，应该返回该菜单的完整信息"""
    # 1. 先建一个菜单
    add_r = MenuApi.add(token, REAL_PARENT_ID, "autotest菜单查详情", TYPE_MENU,
                        order_num=9, path="autotest_detail",
                        component="system/autotest/detail", perms="autotest:detail:list")
    assert add_r.json()["code"] == 200

    # 2. 从列表拿 menuId
    menu_id = _get_menu_id(token, "autotest菜单查详情")

    # 3. 按 id 查
    r = MenuApi.get_by_id(token, menu_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"
    assert body["data"]["menuId"] == menu_id
    assert body["data"]["menuName"] == "autotest菜单查详情"
    assert body["data"]["menuType"] == TYPE_MENU
    assert body["data"]["parentId"] == REAL_PARENT_ID
    assert body["data"]["path"] == "autotest_detail"
    assert body["data"]["component"] == "system/autotest/detail"
    assert body["data"]["perms"] == "autotest:detail:list"


def test_update_menu(token):
    """修改菜单名、排序和 perms，应该成功，且改后能查到新值"""
    # 1. 先建一个按钮
    MenuApi.add(token, REAL_PARENT_ID, "autotest按钮改前", TYPE_BUTTON,
                order_num=1, perms="autotest:upd:before")

    # 2. 从列表里找到它的 menuId
    menu_id = _get_menu_id(token, "autotest按钮改前")

    # 3. 改菜单名 / 排序 / perms
    r = MenuApi.update(token, menu_id, REAL_PARENT_ID, "autotest按钮改后", TYPE_BUTTON,
                       order_num=7, perms="autotest:upd:after")
    assert r.status_code == 200
    assert r.json()["code"] == 200
    assert r.json()["msg"] == "操作成功"

    # 4. 回查，确认改了
    detail_r = MenuApi.get_by_id(token, menu_id)
    data = detail_r.json()["data"]
    assert data["menuName"] == "autotest按钮改后"
    assert data["orderNum"] == 7
    assert data["perms"] == "autotest:upd:after"


def test_delete_menu(token):
    """删除菜单，应该成功，且列表里查不到。
    菜单删除是**物理删除**（sys_menu 没有 del_flag 列），
    所以单查时断言'没有 data 字段'，这跟部门模块相反"""
    # 1. 先建一个菜单
    MenuApi.add(token, REAL_PARENT_ID, "autotest菜单待删", TYPE_BUTTON,
                order_num=9, perms="autotest:del:btn")

    # 2. 从列表拿 menuId
    menu_id = _get_menu_id(token, "autotest菜单待删")

    # 3. 删
    r = MenuApi.delete(token, menu_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["msg"] == "操作成功"

    # 4. 回查：列表里应该查不到
    names = _get_menu_names(token)
    assert "autotest菜单待删" not in names, f"删除后列表里仍能查到该菜单：{names}"

    # 5. 物理删除的标志：按 id 单查也不会再有 data 字段
    detail_r = MenuApi.get_by_id(token, menu_id)
    assert detail_r.json()["code"] == 200
    assert "data" not in detail_r.json(), f"菜单是物理删除，单查不该再有 data：{detail_r.json()}"


def test_delete_menu_with_children_rejected(token):
    """删除有子菜单的父菜单，应该被拒（code=601）"""
    # 1. 建一个父菜单（C 类型）
    parent_r = MenuApi.add(token, REAL_PARENT_ID, "autotest父菜单", TYPE_MENU,
                           order_num=1, path="autotest_parent",
                           component="system/autotest/parent", perms="autotest:parent:list")
    assert parent_r.json()["code"] == 200
    parent_id = _get_menu_id(token, "autotest父菜单")

    # 2. 在它下面建子菜单（F 类型）
    child_r = MenuApi.add(token, parent_id, "autotest子菜单", TYPE_BUTTON,
                          order_num=1, perms="autotest:child:btn")
    assert child_r.json()["code"] == 200

    # 3. 删父菜单，应该被拒
    r = MenuApi.delete(token, parent_id)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 601, f"有子菜单时应返回 601，实际：{body}"
    assert body["msg"] == "存在子菜单,不允许删除"

    # 4. 回查：父菜单还在列表里
    assert "autotest父菜单" in _get_menu_names(token)

    # 5. 收尾：先删子再删父，避免给其他用例留垃圾数据
    child_id = _get_menu_id(token, "autotest子菜单")
    assert MenuApi.delete(token, child_id).json()["code"] == 200
    assert MenuApi.delete(token, parent_id).json()["code"] == 200


def test_add_duplicate_menu_name(token):
    """重复新增同名菜单，应该被拒（menuName 是全局唯一，不分父级）"""
    # 1. 建第一个
    r1 = MenuApi.add(token, REAL_PARENT_ID, "autotest菜单重名", TYPE_BUTTON,
                     order_num=1, perms="autotest:dup:first")
    assert r1.json()["code"] == 200

    # 2. 再建同名，应该失败。注意换个 perms 也没用，卡的是 menuName
    r2 = MenuApi.add(token, REAL_PARENT_ID, "autotest菜单重名", TYPE_BUTTON,
                     order_num=2, perms="autotest:dup:second")
    assert r2.status_code == 200
    body = r2.json()
    assert body["code"] != 200, f"同名菜单应该被拒绝，实际返回：{body}"
    assert "菜单名称已存在" in body["msg"]

    # 3. 回查：列表里只能有一个 autotest菜单重名，且 perms 还是第一个的
    menus = _get_all_menus(token)
    dups = [m for m in menus if m["menuName"] == "autotest菜单重名"]
    assert len(dups) == 1, f"同名菜单只应存在一条，实际 {len(dups)} 条"
    assert dups[0]["perms"] == "autotest:dup:first"


def test_add_duplicate_perms_allowed(token):
    """perms 允许重复 —— 这是菜单和角色/岗位/用户都不一样的地方，反向锁住这个行为"""
    # 1. 建第一个按钮
    r1 = MenuApi.add(token, REAL_PARENT_ID, "autotest按钮perms甲", TYPE_BUTTON,
                     order_num=1, perms="autotest:sameperms:query")
    assert r1.json()["code"] == 200

    # 2. 用同一个 perms 建第二个按钮，应该成功（perms 不唯一）
    r2 = MenuApi.add(token, REAL_PARENT_ID, "autotest按钮perms乙", TYPE_BUTTON,
                     order_num=2, perms="autotest:sameperms:query")
    assert r2.status_code == 200
    body = r2.json()
    assert body["code"] == 200, f"perms 允许重复，这里期望成功，实际：{body}"

    # 3. 回查：两条都在，且 perms 相同
    menus = _get_all_menus(token)
    same = [m for m in menus if m["perms"] == "autotest:sameperms:query"]
    assert len(same) == 2, f"同perms 应有2 条菜单，实际 {len(same)} 条"
    assert {m["menuName"] for m in same} == {"autotest按钮perms甲", "autotest按钮perms乙"}


def test_add_menu_without_required_fields(token):
    """新增菜单缺必填字段，应该被拒（三种类型的必填字段完全一样：menuName / menuType / orderNum）"""
    # 1. 不给 menuName —— 三种类型都试一遍，报错都一样
    for t in [TYPE_DIR, TYPE_MENU, TYPE_BUTTON]:
        r = MenuApi.add(token, REAL_PARENT_ID, "", t, order_num=9, path="autotest_x")
        assert r.status_code == 200
        assert r.json()["code"] == 500, f"menuType={t} 缺 menuName 应报 500"
        assert r.json()["msg"] == "菜单名称不能为空"

    # 2. 不给 menuType
    r2 = MenuApi.add(token, REAL_PARENT_ID, "autotest菜单无类型", "", order_num=9, path="x")
    assert r2.status_code == 200
    assert r2.json()["code"] == 500
    assert r2.json()["msg"] == "菜单类型不能为空"

    # 3. 不给 orderNum
    r3 = MenuApi.add(token, REAL_PARENT_ID, "autotest菜单无排序", TYPE_MENU,
                     order_num=None, path="x", component="system/x/index")
    assert r3.status_code == 200
    assert r3.json()["code"] == 500
    assert r3.json()["msg"] == "显示顺序不能为空"

    # 4. 回查：这些失败的新增都不该落库
    names = _get_menu_names(token)
    assert "autotest菜单无类型" not in names, f"校验失败的菜单却落库了，现有：{names}"
    assert "autotest菜单无排序" not in names, f"校验失败的菜单却落库了，现有：{names}"


def test_add_menu_optional_fields_not_required(token):
    """path / component / perms 都不是必填 —— 探路发现这点时挺意外，反向锁住这个行为。

    RuoYi 菜单的必填字段只有 menuName / menuType / orderNum 三个，
    目录不给 path、菜单不给 component、按钮不给 perms 都能建成功。

    ⚠️ 重要：本用例造出的数据**必须在用例结束时立刻删掉**。
    这类脏数据会进getRouters 的路由表，导致前端 vue-router 抛
    "Cannot read properties of undefined (reading 'replace')"，整个前端白屏。
    所以这里用 try/finally 强制收尾，不能只依赖 conftest 的跑前清理——
    跑前清理救不了「跑完到下次开跑之间」这段时间。"""
    created_ids = []
    try:
        # 1. 目录不给 path（path 落库为空字符串，路由表里就是个空 path）
        r1 = MenuApi.add(token, REAL_PARENT_ID, "autotest目录无path", TYPE_DIR, order_num=9)
        assert r1.status_code == 200
        assert r1.json()["code"] == 200, f"目录不给 path 应该能建成功，实际：{r1.json()}"

        # 2. 菜单不给 component 和 perms
        r2 = MenuApi.add(token, REAL_PARENT_ID, "autotest菜单无组件", TYPE_MENU,
                         order_num=9, path="autotest_nocomp")
        assert r2.status_code == 200
        assert r2.json()["code"] == 200, f"菜单不给 component 应该能建成功，实际：{r2.json()}"

        # 3. 按钮不给 perms（按钮不进路由表，污染最小）
        r3 = MenuApi.add(token, REAL_PARENT_ID, "autotest按钮无perms", TYPE_BUTTON, order_num=9)
        assert r3.status_code == 200
        assert r3.json()["code"] == 200, f"按钮不给 perms 应该能建成功，实际：{r3.json()}"

        # 4. 回查：三条都真的落库了，且按钮的 perms 为空
        menus = _get_all_menus(token)
        names = [m["menuName"] for m in menus]
        assert "autotest目录无path" in names
        assert "autotest菜单无组件" in names
        assert "autotest按钮无perms" in names
        btn = next(m for m in menus if m["menuName"] == "autotest按钮无perms")
        assert not btn["perms"], f"按钮没给 perms，落库后应为空，实际 {btn['perms']!r}"

        # 记下 id 供finally 清理
        created_ids = [m["menuId"] for m in menus
                       if m["menuName"] in ("autotest目录无path", "autotest菜单无组件",
                                            "autotest按钮无perms")]
    finally:
        # 无论断言是否失败，都必须把脏菜单删掉，否则前端会白屏
        for name in ("autotest目录无path", "autotest菜单无组件", "autotest按钮无perms"):
            try:
                mid = _get_menu_id(token, name)
                MenuApi.delete(token, mid)
            except Exception:
                pass  # 已经不在列表里就算了
        left = [m for m in _get_all_menus(token)
                if m["menuName"] in ("autotest目录无path", "autotest菜单无组件",
                                    "autotest按钮无perms")]
        assert not left, f"脏菜单没清干净，会导致前端白屏：{[m['menuName'] for m in left]}"


def test_add_root_menu(token):
    """parentId传 0 可以建根菜单 —— 菜单和部门不一样（部门不允许建根）。

    ⚠️ 根菜单同样会进 getRouters 路由表，用完必须立刻删掉，否则前端白屏。"""
    try:
        r = MenuApi.add(token, 0, "autotest根菜单", TYPE_DIR,
                        order_num=9, path="autotest_root")
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200, f"parentId=0 建根菜单应该成功，实际：{body}"
        assert body["msg"] == "操作成功"

        # 回查：确实是一个 parentId=0 的根菜单
        menus = _get_all_menus(token)
        hit = next((m for m in menus if m["menuName"] == "autotest根菜单"), None)
        assert hit, f"新增后列表里找不到该根菜单，现有：{_get_menu_names(token)}"
        assert hit["parentId"] == 0
    finally:
        # 根菜单会进路由表，必须立刻清掉
        try:
            rid = _get_menu_id(token, "autotest根菜单")
            MenuApi.delete(token, rid)
        except Exception:
            pass
        left = [m for m in _get_all_menus(token) if m["menuName"] == "autotest根菜单"]
        assert not left, "根菜单没清干净，会导致前端白屏"