"""通知公告相关接口封装"""
import requests
from config import API_BASE_URL


class NoticeApi:
    """通知公告接口。

    探路确认的几个特点：
    1. 列表是标准的 {total, rows, code, msg}，**分页有效**（pageSize / pageNum 都生效）。
       过滤条件只有 noticeTitle（like 模糊）、noticeType（精确）、createBy（like 模糊）三个。
       ⚠️ 传 **status 会被静默忽略** —— SQL 的 where 里根本没有 status 条件
       （所以 status=0 会返回全部，看着"对"其实是巧合，别被误导）。
       列表**没有 order by**，返回顺序就是存储顺序（实测按 notice_id 升序）。
    2. sys_notice **没有 del_flag 列**，删除是**物理删除**，删完按 id 单查也不会再有 data。
    3. 实体上**只有 noticeTitle 是 @NotBlank**（「公告标题不能为空」），
       noticeType / noticeContent / status 都没标必填。
       但！**DB 层 notice_type 是 NOT NULL 且没有默认值**，而 insertNotice 的 XML 又是
       "非空才拼进 SQL"，所以**只传 noticeTitle 会直接抛 SQL 异常**：
       「Field 'notice_type' doesn't have a default value」。
       → 实际结论：**建数据必须带 noticeType**，否则 500。
       （notice_content 在 DB 里是 longblob 且可空，确实不用传。status 有默认 '0'。）
    4. noticeTitle **不唯一**（表上没有唯一索引，后端也不查重），重名会老老实实落两条。
    5. noticeTitle 有两道额外的校验（这是它比别的模块严的地方）：
       - @Xss：「公告标题不能包含脚本字符」
       - @Size(max=50)：「公告标题不能超过50个字符」（DB 列也是 varchar(50)）
    6. 【与其他模块不同】删除一个**不存在**的 noticeId 报的是
       code=500 且 msg=**「操作失败」** —— 因为 deleteNoticeByIds 返回 0 行，
       toAjax(0) 走的是 error() 分支。不是 dict_data/config 那种 msg=null 的 NPE。
    """

    @staticmethod
    def get_list(token, notice_title=None, notice_type=None, create_by=None, page_size=100):
        """查询通知公告列表，返回响应对象。
        page_size 默认 100，避免分页漏数据（这个接口分页是真的生效的）。
        notice_title / create_by 是 like 模糊匹配，notice_type 是精确匹配。
        注意：**status 不支持过滤**，别传了以为生效。"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {"pageNum": 1, "pageSize": page_size}
        if notice_title is not None:
            params["noticeTitle"] = notice_title
        if notice_type is not None:
            params["noticeType"] = notice_type
        if create_by is not None:
            params["createBy"] = create_by
        return requests.get(
            f"{API_BASE_URL}/system/notice/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def get_by_id(token, notice_id):
        """按 id 查询单条通知公告，返回响应对象。
        查不存在的 notice_id 返回 code=200 且无 data 字段（物理删除）"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(
            f"{API_BASE_URL}/system/notice/{notice_id}", headers=headers
        )

    @staticmethod
    def add(token, notice_title, notice_type="1", notice_content=None, status="0"):
        """新增通知公告，返回响应对象。

        ⚠️ notice_type 必须传 —— 实体上它没标 @NotBlank，但 DB 列是 NOT NULL 无默认值，
        不传会抛 SQL 异常「Field 'notice_type' doesn't have a default value」。
        这里给默认值 "1"（通知），防呆。

        notice_title 缺了报「公告标题不能为空」，含脚本字符报「公告标题不能包含脚本字符」，
        超过 50 字报「公告标题不能超过50个字符」。
        notice_title **不唯一**，重名不会报错。
        notice_content 可以不传；status 不传后端存默认 '0'。"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "noticeTitle": notice_title,
            "noticeType": notice_type,
        }
        if notice_content is not None:
            payload["noticeContent"] = notice_content
        if status is not None:
            payload["status"] = status
        return requests.post(
            f"{API_BASE_URL}/system/notice",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def update(token, notice_id, notice_title, notice_type=None,
               notice_content=None, status=None):
        """修改通知公告，返回响应对象。notice_id / notice_title 必填。

        只传 notice_id + notice_title 也能改（其余字段 XML 里是"非空才更新"，保持原值）。
        notice_content 传空串 "" 会把内容清掉（这个字段的 XML 条件只判 null 不判空串）。"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "noticeId": notice_id,
            "noticeTitle": notice_title,
        }
        if notice_type is not None:
            payload["noticeType"] = notice_type
        if notice_content is not None:
            payload["noticeContent"] = notice_content
        if status is not None:
            payload["status"] = status
        return requests.put(
            f"{API_BASE_URL}/system/notice",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def delete(token, notice_id):
        """删除通知公告，返回响应对象。通知公告删除是**物理删除**
        （sys_notice 表没有 del_flag 列），删后列表查不到，按 id 单查也不会再有 data。

        传一个**不存在**的 notice_id 报 code=500、msg「操作失败」。"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.delete(
            f"{API_BASE_URL}/system/notice/{notice_id}",
            headers=headers,
        )
