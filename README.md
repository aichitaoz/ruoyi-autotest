# RuoYi 系统自动化测试框架（UI + 接口）

> 本仓库基于 [RuoYi-Vue v3.8.9](https://gitee.com/y_project/RuoYi-Vue)，在其上搭建了一套
> **Python + pytest** 的自动化测试框架，用于回归验证若依后台的接口与页面。
> 上游原始说明已被本文件覆盖，需要时用 `git show HEAD:README.md` 取回。

**当前进度：接口自动化 11 个模块、114 条用例，全绿。** UI 自动化刚起步。

---

## 一、快速开始

### 1. 服务环境

四个服务都跑在 Docker 容器里：

| 组件 | 地址 | 容器 |
|---|---|---|
| 后端 | `http://localhost:8080` | `ruoyi-admin` |
| 前端 | `http://localhost`（反代 `/prod-api` → 8080） | `ruoyi-nginx` |
| MySQL 5.7 | `localhost:3306`，库 `ry-vue`，`root/root` | `ruoyi-mysql` |
| Redis | `localhost:6379` | `ruoyi-redis` |

```bash
docker ps    # 确认四个容器都是 Up
```

登录账号：`admin / admin123`

### 2. Python 环境

**解释器不在 PATH 上** —— `python` 命令指向的是 WorkBuddy 托管的 3.13，没装 requests。
要用这个 venv：

```
C:\Users\xbw\.workbuddy\binaries\python\envs\default\Scripts\python.exe
```

已装：`requests` / `pymysql` / `pytest` / `pytest-html` / `selenium`。

### 3. 跑测试

```bash
PY=C:/Users/xbw/.workbuddy/binaries/python/envs/default/Scripts/python.exe

$PY -m pytest tests_api/ -v                          # 全部接口测试
$PY -m pytest tests_api/test_dict_data_api.py -v    # 只跑一个模块
$PY -m pytest tests/ -v                             # UI 测试（Selenium）
```

`pytest.ini` 已配 `--html=reports/report.html --self-contained-html`，跑完自动出报告。
根 `conftest.py` 会在 **UI 用例**失败时自动截图并嵌进报告（存 `screenshots/`）。

---

## 二、目录结构

```
D:\RuoYi-Vue
├── api/                    # 接口封装，一个模块一个类，全是 @staticmethod
│   ├── auth_api.py         #   登录 / 取 token
│   ├── user_api.py  role_api.py  post_api.py
│   ├── dept_api.py  menu_api.py
│   ├── dict_type_api.py  dict_data_api.py
│   ├── config_api.py  notice_api.py
│   └── operlog_api.py      #   操作日志（只读模块）
├── tests_api/              # 接口测试用例
│   ├── conftest.py         #   共享 fixture：token + 各模块跑前清理
│   └── test_*_api.py       #   11 个模块
├── pages/                  # UI Page Object（Selenium）
├── tests/                  # UI 测试用例
├── data/users.csv          # UI 测试数据
├── config.py               # 全局配置（地址、账号、DB 连接）
├── conftest.py             # 根 conftest：UI 失败自动截图
├── pytest.ini
├── reports/report.html     # 测试报告
└── screenshots/            # 失败截图
```

**分层约定**：接口封装（`api/`）只负责发请求、**不写任何断言**；断言全部在用例里。
封装类的 docstring 里写该模块"探路确认"的行为特征 —— 那是给写用例的人看的。

---

## 三、已完成模块

| # | 模块 | 接口前缀 | 用例 | 关键点 |
|---|---|---|---|---|
| 1 | 登录认证 | `/login` `/getInfo` | 6 | token 会话内复用；错密码、无 token、错 scheme |
| 2 | 用户管理 | `/system/user` | 7 | **软删**（del_flag=2） |
| 3 | 角色管理 | `/system/role` | 8 | roleKey 唯一；**软删** |
| 4 | 岗位管理 | `/system/post` | 9 | postCode 唯一；物理删 |
| 5 | 部门管理 | `/system/dept` | 10 | 树形；有下级部门/有用户时拒删（601）；**软删** |
| 6 | 菜单管理 | `/system/menu` | 13 | 树形；有子菜单时拒删（601）；物理删 |
| 7 | 字典类型 | `/system/dict/type` | 12 | dictType 唯一 + **有正则格式校验**；被数据引用时拒删（500） |
| 8 | 字典数据 | `/system/dict/data` | 12 | **依赖字典类型**；dictValue 不唯一；无格式校验 |
| 9 | 参数配置 | `/system/config` | 14 | configKey 唯一（代码层）；内置参数禁删 |
| 10 | 通知公告 | `/system/notice` | 12 | **建数据必须带 noticeType** |
| 11 | 操作日志 | `/monitor/operlog` | 11 | **只读模块**，重点测多条件筛选（AND） |

合计 **114 条，全绿**（约 22s）。

---

## 四、测试数据与清理约定

### 数据前缀

所有测试数据一律用 `autotest` 前缀，清理就是 `LIKE 'autotest%'`，不会误伤内置数据。

| 模块 | 关键数据 |
|---|---|
| 字典类型 | `dictType = autotest_data_type_01` |
| 字典数据 | `dictLabel = autotest标签01`、`dictValue = autotest_val_01` |
| 参数配置 | `configKey = autotest.config.key`、`configName = autotest配置01` |
| 通知公告 | `noticeTitle = autotest公告01` |
| 用户 / 角色 / 岗位 / 部门 / 菜单 | 各自的 name、key 以 `autotest` 开头 |

### 清理是**双保险**

1. **跑前清**：`tests_api/conftest.py` 里每模块一个 session 级 autouse fixture，
   开跑前用 SQL 删一遍 `autotest` 数据。
2. **跑完清**：每条造数据的用例内部用 `try/finally` + `_purge()` 走接口删掉自己造的数据。

第 2 条是踩过坑才加的：**只靠"跑前清"救不了「跑完 → 下次开跑」这段窗口**，
这段时间脏数据一直躺在库里。菜单模块曾造出"空 path 菜单"，
它进了 `getRouters` 路由表，把 vue-router 搞崩，**整个前端白屏**。

实测残留对比：

| | 跑完后的 autotest 残留 |
|---|---|
| 只靠"跑前清"的 5 个老模块 | 5~8 条 |
| 加了"跑完清"的新模块 | **0 条** |

### ⚠️ fixture 顺序：pytest 按**名字排序**，不是按定义顺序

有依赖关系的清理（比如"先清字典数据、再清字典类型"）靠的是**名字的字母序**：

```
_cleanup_dict_data_before_api_session  <  _cleanup_dict_types_before_api_session
                         d  <  t
```

实测验证过：把 `_cleanup_zzz_probe` 和 `_cleanup_aaa_probe` 按「zzz 先定义、aaa 后定义」
写进 conftest，跑出来是 **aaa 在最前、zzz 在最后**。实际执行序就是字母序：
`users → configs → depts → dict_data → dict_types → menus → notices → posts → roles`

**所以**：新增有依赖关系的清理 fixture，光把物理位置摆对**是靠不住的**，
必须让名字的字母序正确。`conftest.py` 里也写了这条注释备忘。

---

## 五、各模块"探路结论"速查

> 都是实测出来的，**别凭直觉改**。详细版在对应 `api/xxx_api.py` 的类 docstring 里。

### 删除语义（最容易搞混的一张表）

| 模块 | 表有 `del_flag`？ | 接口删除行为 | 删后按 id 单查 |
|---|---|---|---|
| 用户 / 角色 / 部门 | ✅ 有 | **软删** | 还能查到（`"data" in body`） |
| 岗位 / 字典类型 / 字典数据 / 参数 / 公告 / 菜单 | ❌ 无 | **物理删** | 没有 data（`"data" not in body`） |

**验证删除一律走列表接口**（老规矩）：软删是"列表查不到但单查还在"，
物理删是"列表查不到且单查也没了"。

### 列表返回结构也不统一

| 模块 | 结构 |
|---|---|
| 大部分（用户/角色/岗位/字典/参数/公告/日志） | `{total, rows, code, msg}`，分页有效 |
| **部门 / 菜单** | **树形 `data`，没有 `total` / `rows`** |

### 报错文案里的坑

| 现象 | 说明 |
|---|---|
| 「参数键名**长度**不能为空」 | 后端文案瑕疵，多了"长度"二字，原文如此 |
| 「内置参数【xxx】不能删除 」 | 末尾带一个空格，断言只能用 `in`，不能用等号 |
| 必填字段**多个同时为空**时，文案**随机跳变** | Hibernate Validator 的错误顺序无契约保证（实测空 JSON 跑 10 次三种文案都出现过）。只缺**一个**字段时文案才稳定 |
| 多个校验失败时只返回**一条** msg | 一次只能看到一个字段的错，想全覆盖得逐个字段单独试 |

### 删不存在的 id 会怎样（各模块不一样）

| 模块 | 表现 | 成因 |
|---|---|---|
| 字典数据 / 参数配置 | `code=500`，**`msg` 是 null** | service 里 `selectById` 拿到 null 后直接 NPE |
| 通知公告 / 操作日志 | `code=500`，`msg=「操作失败」` | service 返回 0 行，`toAjax(0)` 走 error() 分支 |

### 各模块的"意外行为"（都已写成用例锁住）

- **字典数据**：用**不存在的 `dictType`** 建数据会**建成功** → 产生挂不到任何类型上的孤儿数据。
  这说明"数据依赖类型"这条规则**只靠调用方自觉**，所以每条造数用例第一步都必须先建类型。
- **字典数据**：`dictValue` **不唯一**；`dictType` **没有**格式校验
  （大写 / 短横线 / 点号 / 数字开头 / 中文全都能建，跟字典类型模块正好相反）。
- **参数配置**：`@Validated` 作用在整个 body 上 → **修改时也必须带 `configKey`**，
  只传 `configId` + `configValue` 会被必填校验拦下。
- **通知公告**：实体上只有 `noticeTitle` 标了必填，但 **DB 里 `notice_type` 是 NOT NULL 无默认值**，
  而 insert 的 XML 又是"非空才拼进 SQL" → **只传 `noticeTitle` 直接抛 SQL 异常**。
- **通知公告**：列表**不支持 status 过滤**（SQL 里没这个条件，传了被静默忽略），且**无 order by**。
- **操作日志**：**没有** get_by_id 接口；多条件是 **AND**（已用"把某个条件换成不可能值 → total 归零"钉死）。

---

## 六、红线

1. **绝对不要调 `DELETE /monitor/operlog/clean`**
   它对应 `truncate table sys_oper_log`，一调用就**清空所有人的操作日志**，不可恢复。
   所以 `OperLogApi` 里**故意没封装 `clean` 方法**。

2. **操作日志的 `total` 不能写死数字**
   这张表是测试自己在污染的 —— 每调一次带 `@Log` 的接口就多一行（已 1700+）。
   只能断言 `>=N`、`==0`、或"两次查询相等"。

3. **会进 `getRouters` 路由表的表（菜单、部门）要特别小心空 path**
   脏数据会让 vue-router 崩、前端白屏。

4. **造完数据立刻在用例内删掉**，别只依赖 conftest 的"跑前清"（见第四节）。

5. **探路脚本一律命名 `_probe_*.py`，跑完删掉**，别留在仓库根目录。

---

## 七、UI 自动化（进行中）

Selenium + Page Object：

```
pages/base_page.py     # open / find / click / input_text / wait_text ...
pages/login_page.py
pages/user_page.py
tests/test_login.py
tests/test_user.py
```

目前只覆盖登录和用户管理，属起步阶段。接口侧已有 114 条，
**建议先把接口侧做完，UI 侧按需补**。

---

## 八、待办

- [ ] UI 侧：菜单、字典等核心页面的冒烟用例
- [ ] 接口侧边角模块：`/monitor/logininfor`、`/monitor/online`、`/system/user/profile`

---

## 九、致谢

上游项目：[RuoYi-Vue](https://gitee.com/y_project/RuoYi-Vue) v3.8.9（MIT）。
本仓库的改动集中在根目录这套 Python 测试框架，`ruoyi-*` 下的 Java 后端代码基本未动。
上游原始 README：`git show HEAD:README.md`
