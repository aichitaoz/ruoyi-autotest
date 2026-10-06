"""参数配置相关接口封装"""
import requests
from config import API_BASE_URL


class ConfigApi:
    """参数配置接口。

    探路确认的几个特点：
    1. 列表是标准的 {total, rows, code, msg}，**分页有效**（pageSize / pageNum 都生效）；
       过滤条件支持 configName（like 模糊）、configKey（like 模糊）、configType（精确）。
       注意 configKey 是**模糊**匹配，按 "autotest.config.key" 过滤会连
       "autotest.config.key_b" 一起捞出来。
    2. sys_config **没有 del_flag 列**，删除是**物理删除**，删完按 id 单查也不会再有 data。
    3. configName / configKey / configValue 三个都必填（实体上 @NotBlank）：
       「参数名称不能为空」/「参数键名长度不能为空」（原文如此，多了"长度"两个字，
       是后端文案瑕疵）/「参数键值不能为空」。
       **configType 不是必填**，不传走 DB 默认值 "N"。
    4. configKey 唯一，但**唯一性是代码层 checkConfigKeyUnique 做的**，
      DB 上只有主键索引、没有唯一索引。新增重复报
       「新增参数'xxx'失败，参数键名已存在」，修改撞车报
       「修改参数'xxx'失败，参数键名已存在」——都嵌了参数名，断言要用 in 而不是等号。
       注意：**修改和自己同名是允许的**（checkConfigKeyUnique 会排除自身 configId）。
    5. 因为 @Validated 作用在整个请求体上，**修改时也必须带上 configKey**，
       只传 configId + configValue 会报「参数键名长度不能为空」。
    6. **内置参数（configType="Y"）不允许删除**：SysConfigServiceImpl.deleteConfigByIds
       会先查一次，configType 是 "Y" 就抛 ServiceException
       「内置参数【xxx】不能删除 」（注意末尾有个空格），返回 code=500。
       configType="N" 的（包括我们自己建的）能正常删。
    7. 【后端缺陷】删除一个**不存在**的 configId：
       deleteConfigByIds 里 `selectConfigById(configId)` 拿到 null，
       紧接着 `config.getConfigType()` 就抛 NPE，被全局异常处理器兜成
       code=500 且 **msg 是 null**（不是中文提示）。
    """

    @staticmethod
    def get_list(token, config_name=None, config_key=None, config_type=None, page_size=100):
        """查询参数配置列表，返回响应对象。
        page_size 默认 100，避免分页漏数据（这个接口分页是真的生效的）。
        config_name / config_key 是 like 模糊匹配，config_type 是精确匹配。"""
        headers = {"Authorization": f"Bearer {token}"}
        params = {"pageNum": 1, "pageSize": page_size}
        if config_name is not None:
            params["configName"] = config_name
        if config_key is not None:
            params["configKey"] = config_key
        if config_type is not None:
            params["configType"] = config_type
        return requests.get(
            f"{API_BASE_URL}/system/config/list",
            headers=headers,
            params=params,
        )

    @staticmethod
    def get_by_id(token, config_id):
        """按 id 查询单条参数配置，返回响应对象。
        查不存在的 config_id 返回 code=200 且无 data 字段（物理删除）"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.get(
            f"{API_BASE_URL}/system/config/{config_id}", headers=headers
        )

    @staticmethod
    def add(token, config_key, config_name, config_value, config_type=None):
        """新增参数配置，返回响应对象。
        config_key / config_name / config_value 三个必填，缺了分别报
        「参数键名长度不能为空」「参数名称不能为空」「参数键值不能为空」；
        configKey 重复报「新增参数'{config_name}'失败，参数键名已存在」；
        config_type 不是必填，不传后端存 "N"（非系统内置）。"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "configKey": config_key,
            "configName": config_name,
            "configValue": config_value,
        }
        if config_type is not None:
            payload["configType"] = config_type
        return requests.post(
            f"{API_BASE_URL}/system/config",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def update(token, config_id, config_key, config_name, config_value, config_type=None):
        """修改参数配置，返回响应对象。config_id 必填。

        注意：@Validated 作用在整个请求体上，所以 **config_key / config_name /
        config_value 三个都得带上**，只传 configId + configValue 会被必填校验拦下。
        改成别人已占用的 configKey 报「修改参数'{config_name}'失败，参数键名已存在」；
        改成自己原来的 configKey 是允许的。"""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "configId": config_id,
            "configKey": config_key,
            "configName": config_name,
            "configValue": config_value,
        }
        if config_type is not None:
            payload["configType"] = config_type
        return requests.put(
            f"{API_BASE_URL}/system/config",
            json=payload,
            headers=headers,
        )

    @staticmethod
    def delete(token, config_id):
        """删除参数配置，返回响应对象。参数配置删除是**物理删除**
        （sys_config 表没有 del_flag 列），删后列表查不到，按 id 单查也不会再有 data。

        两种情况会失败：
        - configType="Y" 的内置参数：500「内置参数【xxx】不能删除 」
        - **不存在**的 config_id：500 且 msg 为 null（后端 NPE 路径）"""
        headers = {"Authorization": f"Bearer {token}"}
        return requests.delete(
            f"{API_BASE_URL}/system/config/{config_id}",
            headers=headers,
        )
