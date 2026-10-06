"""接口测试的共享 fixture"""
import pymysql
import pytest
from api.auth_api import AuthApi
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def cleanup_test_users():
    """用 SQL 清掉所有测试用户（用户名以 autotest 开头）"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM sys_user WHERE user_name LIKE 'autotest%%'")
            deleted = cursor.rowcount
        conn.commit()
        print(f"[clean] 已清理 {deleted} 个测试用户")
    finally:
        conn.close()


def cleanup_test_roles():
    """用 SQL 清掉所有测试角色（role_key 或 role_name 以 autotest 开头）。
    角色删的是软删除记录，所以这里走物理删除，顺便清掉角色菜单、角色部门关联，避免残留。"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT role_id FROM sys_role "
                "WHERE role_key LIKE 'autotest%%' OR role_name LIKE 'autotest%%'"
            )
            role_ids = [row[0] for row in cursor.fetchall()]
            if role_ids:
                placeholders = ",".join(["%s"] * len(role_ids))
                cursor.execute(
                    f"DELETE FROM sys_role_menu WHERE role_id IN ({placeholders})", role_ids
                )
                cursor.execute(
                    f"DELETE FROM sys_role_dept WHERE role_id IN ({placeholders})", role_ids
                )
                cursor.execute(
                    f"DELETE FROM sys_role WHERE role_id IN ({placeholders})", role_ids
                )
                deleted = cursor.rowcount
            else:
                deleted = 0
        conn.commit()
        print(f"[clean] 已清理 {deleted} 个测试角色")
    finally:
        conn.close()

def cleanup_test_posts():
    """用 SQL 清掉所有测试岗位（post_code 或 post_name 以 autotest 开头）。
    sys_post 表没有 del_flag 列，接口删岗位就是物理删除，所以这里同样物理删除；
    先清 sys_user_post（岗位-用户中间表，只有 user_id / post_id 两列）再删岗位本身。"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT post_id FROM sys_post "
                "WHERE post_code LIKE 'autotest%%' OR post_name LIKE 'autotest%%'"
            )
            post_ids = [row[0] for row in cursor.fetchall()]
            if post_ids:
                placeholders = ",".join(["%s"] * len(post_ids))
                cursor.execute(
                    f"DELETE FROM sys_user_post WHERE post_id IN ({placeholders})", post_ids
                )
                cursor.execute(
                    f"DELETE FROM sys_post WHERE post_id IN ({placeholders})", post_ids
                )
                deleted = cursor.rowcount
            else:
                deleted = 0
        conn.commit()
        print(f"[clean] 已清理 {deleted} 个测试岗位")
    finally:
        conn.close()


def cleanup_test_depts():
    """用 SQL 清掉所有测试部门（dept_name 以 autotest 开头）。
    部门是树形结构，ancestors 形如 "0,100,101"，逗号段数越多层级越深，
    所以按段数倒序删（深的先删、浅的后删），避免父部门被子部门卡住。
    sys_dept 没有外键约束指向它，物理删除即可。"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT dept_id, ancestors FROM sys_dept "
                "WHERE dept_name LIKE 'autotest%%'"
            )
            rows = cursor.fetchall()
            if rows:
                # ancestors 段数多的（层级深的）排前面先删
                ordered = sorted(
                    rows,
                    key=lambda x: len(str(x[1] or "").split(",")) if x[1] else 0,
                    reverse=True,
                )
                dept_ids = [r[0] for r in ordered]
                placeholders = ",".join(["%s"] * len(dept_ids))
                cursor.execute(
                    f"DELETE FROM sys_dept WHERE dept_id IN ({placeholders})", dept_ids
                )
                deleted = cursor.rowcount
            else:
                deleted = 0
        conn.commit()
        print(f"[clean] 已清理 {deleted} 个测试部门")
    finally:
        conn.close()


def cleanup_test_menus():
    """用 SQL 清掉所有测试菜单（menu_name 或 perms 以 autotest 开头）。
    菜单表 sys_menu **没有 ancestors 列**（部门才有），层级只能靠 parent_id 判断，
    所以按 menu_id 倒序删：子菜单后建、id 更大，倒序即先子后父。
    菜单被角色引用走 sys_role_menu（role_id / menu_id 两列），先清关联再删菜单。"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT menu_id, parent_id FROM sys_menu "
                "WHERE menu_name LIKE 'autotest%%' OR perms LIKE 'autotest%%'"
            )
            rows = cursor.fetchall()
            if rows:
                # 按 menu_id 倒序删：子菜单总是后建、id 比父菜单大，倒序就是先子后父，
                # 这样删父菜单时子菜单已经不在了（走 SQL 不受接口的 601 约束限制）
                ordered = sorted(rows, key=lambda x: x[0], reverse=True)
                menu_ids = [r[0] for r in ordered]
                placeholders = ",".join(["%s"] * len(menu_ids))
                cursor.execute(
                    f"DELETE FROM sys_role_menu WHERE menu_id IN ({placeholders})", menu_ids
                )
                cursor.execute(
                    f"DELETE FROM sys_menu WHERE menu_id IN ({placeholders})", menu_ids
                )
                deleted = cursor.rowcount
            else:
                deleted = 0
        conn.commit()
        print(f"[clean] 已清理 {deleted} 个测试菜单")
    finally:
        conn.close()


def cleanup_test_dict_data():
    """用 SQL 清掉所有测试字典数据（dict_type 或 dict_label 以 autotest 开头）。
    sys_dict_data 没有 del_flag 列（全表只有 dict_code 一个主键索引），接口删数据就是
    物理删除，所以这里同样物理删除。

    ⚠️ 这个函数必须在 cleanup_test_dict_types() **之前**执行。
    原因：sys_dict_data 靠 dict_type 这个**字符串**指向 sys_dict_type.dict_type，
    两表之间**没有外键约束**，所以「先删类型」不会报错，但会把数据变成孤儿 ——
    列表里还查得到、按 dictType 过滤也筛得出来，却挂不到任何类型上，极难排查。
    （接口层对此毫无保护：用不存在的 dictType 建数据都能成功。）"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM sys_dict_data "
                "WHERE dict_type LIKE 'autotest%%' OR dict_label LIKE 'autotest%%'"
            )
            deleted = cursor.rowcount
        conn.commit()
        print(f"[clean] 已清理 {deleted} 条测试字典数据")
    finally:
        conn.close()


def cleanup_test_dict_types():
    """用 SQL 清掉所有测试字典类型（dict_name 或 dict_type 以 autotest 开头）。
    sys_dict_type 没有 del_flag 列，接口删类型就是物理删除，所以这里同样物理删除。
    表上有 dict_type 唯一索引，但没有外键约束指向它，直接删即可。
    注意：下一个模块（字典数据）要在这**之前**先清 sys_dict_data，否则会留下孤儿数据。"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM sys_dict_type "
                "WHERE dict_name LIKE 'autotest%%' OR dict_type LIKE 'autotest%%'"
            )
            deleted = cursor.rowcount
        conn.commit()
        print(f"[clean] 已清理 {deleted} 个测试字典类型")
    finally:
        conn.close()


def cleanup_test_configs():
    """用 SQL 清掉所有测试参数配置（config_key 或 config_name 以 autotest 开头）。
    sys_config 没有 del_flag 列，接口删配置就是物理删除，同样物理删除即可。

    注意 config_key 的唯一性是**代码层** checkConfigKeyUnique 做的（DB 上只有主键索引），
    所以这里批量清不会踩唯一约束。
    另外接口对 config_type='Y' 的内置参数有删除保护，SQL 直删不受这个限制 ——
    但我们只会删 autotest 前缀的，碰不到内置参数。"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM sys_config "
                "WHERE config_key LIKE 'autotest%%' OR config_name LIKE 'autotest%%'"
            )
            deleted = cursor.rowcount
        conn.commit()
        print(f"[clean] 已清理 {deleted} 条测试参数配置")
    finally:
        conn.close()


def cleanup_test_notices():
    """用 SQL 清掉所有测试通知公告（notice_title 以 autotest 开头）。
    sys_notice 没有 del_flag 列，接口删公告就是物理删除，同样物理删除即可。
    notice_title 不唯一（无唯一索引），批量删不会踩约束。"""
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM sys_notice WHERE notice_title LIKE 'autotest%%'"
            )
            deleted = cursor.rowcount
        conn.commit()
        print(f"[clean] 已清理 {deleted} 条测试通知公告")
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_before_api_session():
    """接口测试会话开始前，清一次 autotest 用户"""
    cleanup_test_users()

@pytest.fixture(scope="session", autouse=True)
def _cleanup_roles_before_api_session():
    """接口测试会话开始前，清一次 autotest 角色（含角色菜单、角色部门关联）"""
    cleanup_test_roles()

@pytest.fixture(scope="session", autouse=True)
def _cleanup_posts_before_api_session():
    """接口测试会话开始前，清一次 autotest 岗位（含 sys_user_post 关联）"""
    cleanup_test_posts()

@pytest.fixture(scope="session", autouse=True)
def _cleanup_depts_before_api_session():
    """接口测试会话开始前，清一次 autotest 部门（按 ancestors 层级倒序删，深的先删）"""
    cleanup_test_depts()

@pytest.fixture(scope="session", autouse=True)
def _cleanup_menus_before_api_session():
    """接口测试会话开始前，清一次 autotest 菜单（含 sys_role_menu 关联）"""
    cleanup_test_menus()

@pytest.fixture(scope="session", autouse=True)
def _cleanup_dict_data_before_api_session():
    """接口测试会话开始前，清一次 autotest 字典数据。

    ⚠️ 必须排在 _cleanup_dict_types_before_api_session **之前** ——
    字典数据挂在字典类型的 dictType 字符串上，两表又没有外键约束，
    类型先被删掉的话数据就成孤儿了。

    所以这个 fixture 的**物理位置**故意写在 dict_types 那个上面。

    另外补一条实测结论：pytest 对**同 scope 的 autouse fixture 是按 fixture 名字排序
    执行的，不是按定义顺序** —— 实测把 _cleanup_zzz_probe 和 _cleanup_aaa_probe
    按「zzz 先定义、aaa 后定义」写进 conftest，跑出来是 aaa 在最前、zzz 在最后。
    好在 "_cleanup_dict_data_..." < "_cleanup_dict_types_..."（dict_d < dict_t），
    名字序恰好就是我们要的顺序，等于给这段依赖上了**双保险**：
    物理位置满足要求，名字排序也兜住了。"""
    cleanup_test_dict_data()

@pytest.fixture(scope="session", autouse=True)
def _cleanup_dict_types_before_api_session():
    """接口测试会话开始前，清一次 autotest 字典类型"""
    cleanup_test_dict_types()

@pytest.fixture(scope="session", autouse=True)
def _cleanup_configs_before_api_session():
    """接口测试会话开始前，清一次 autotest 参数配置"""
    cleanup_test_configs()

@pytest.fixture(scope="session", autouse=True)
def _cleanup_notices_before_api_session():
    """接口测试会话开始前，清一次 autotest 通知公告"""
    cleanup_test_notices()

@pytest.fixture(scope="session")
def token():
    """整个测试会话登录一次，拿到 token，供所有用例复用"""
    r = AuthApi.login("admin", "admin123")
    body = r.json()
    assert body["code"] == 200, f"登录失败，无法获取 token：{body}"
    return body["token"]