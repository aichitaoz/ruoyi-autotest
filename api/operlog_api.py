"""操作日志相关接口封装（只读模块）"""
import requests
from config import API_BASE_URL


class OperLogApi:
    """操作日志接口。

    这是一个**只读模块**，只有一个查询接口 + 两个删除接口，没有新增和修改：

        GET    /monitor/operlog/list        列表（带筛选、分页）
        DELETE /monitor/operlog/{operIds}   按 id 批量删除
        DELETE /monitor/operlog/clean       ⚠️ truncate 整张表 —— 见下方警告
        POST   /monitor/operlog/export      导出 Excel

    探路确认的几个特点：
    1. 列表是标准的 {total, rows, code, msg}，**分页有效**（pageSize / pageNum 都生效），
       并且固定按 **oper_id 倒序**（最新的日志在最前面）。
    2. **没有按 id 单查的接口**：SysOperLogMapper 里有 selectOperLogById，
       但 SysOperlogController 没把它暴露出来。
       `GET /monitor/operlog/1` 会被当成 DELETE 路由匹配到，返回
       「Request method 'GET' not supported」。
    3. 支持的筛选条件（全部在 SQL 里生效）：
       - title          like 模糊
       - operName       like 模糊
       - businessType   精确（整型，0其它 1新增 2修改 3删除 ...）
       - businessTypes  IN 集合（逗号分隔的整型串，如 "2,3"）
       - status         精确（整型，0正常 1异常）
       - operIp         like 模糊
       - params[beginTime] / params[endTime]   oper_time 的时间范围
       **多个条件之间是 AND 组合**，不是 OR。
    4. sys_oper_log **没有 del_flag 列**；business_type / status / oper_time 上有普通索引，
       所以按这三列筛选是有索引支撑的。
    5. 表是接口测试自己在"污染"的 —— 每次调带 @Log 的接口都会往里写一行，
       实测 1500+ 行且一直在涨。所以**断言 total 时只能用「>=N」「==0」「两次查询相等」**，
       绝不能写死具体数字。

    ⚠️⚠️ **绝对不要调 /monitor/operlog/clean**：它对应 mapper 里的
    `<update id="cleanOperLog">truncate table sys_oper_log</update>`，
    一调就把**整张操作日志表清空**（不是清 autotest 数据，是清所有人的），
    且不可恢复。所以这里**故意不封装 clean 方法**。
    """

    @staticmethod
    def get_list(token, title=None, oper_name=None, business_type=None,
                 business_types=None, status=None, oper_ip=None,
                 begin_time=None, end_time=None, page_size=100):
        """查询操作日志列表，返回响应对象。

        title / oper_name / oper_ip 是 like 模糊匹配；
        business_type / status 是精确匹配；
        business_types 传一个可迭代对象（如 [2, 3]），走 SQL 的 IN；
        begin_time / end_time 传 "yyyy-MM-dd HH:mm:ss" 字符串，
        走 RuoYi 的 params[beginTime] / params[endTime] 约定，按 oper_time 过滤。

        所有条件之间是 AND 组合。page_size 默认 100。"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {"pageNum": 1, "pageSize": page_size}
        if title is not None:
            params["title"] = title
        if oper_name is not None:
            params["operName"] = oper_name
        if business_type is not None:
            params["businessType"] = business_type
        if business_types is not None:
            params["businessTypes"] = ",".join(str(x) for x in business_types)
        if status is not None:
            params["status"] = status
        if oper_ip is not None:
            params["operIp"] = oper_ip
        if begin_time is not None:
            params["params[beginTime]"] = begin_time
        if end_time is not None:
            params["params[endTime]"] = end_time
        return requests.get(
            f"{API_BASE_URL}/monitor/operlog/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def delete_by_ids(token, oper_ids):
        """按 id 批量删除操作日志，返回响应对象。RuoYi 的批量删除接口都是
        `/xxx/{ids}` 这种逗号分隔的路径变量。

        ⚠️ 日志是**生产数据**，测试里只允许拿不存在的 id 来验证接口行为
        （这种调用是 no-op，不会删掉任何真实日志）。
        传不存在的 id：service 返回 0 行 -> toAjax(0) -> code=500、msg「操作失败」。"""
        headers = {"Authorization": f"Bearer {token}"}
        if isinstance(oper_ids, (list, tuple)):
            ids = ",".join(str(x) for x in oper_ids)
        else:
            ids = str(oper_ids)
        return requests.delete(
            f"{API_BASE_URL}/monitor/operlog/{ids}",
            headers=headers,
        )
