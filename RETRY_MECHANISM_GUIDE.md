# 🔄 LLM API 重试机制指南

## 📋 概述

PromptSplit 系统现在配备了**智能重试机制**，能够自动处理 LLM API 调用失败的情况，显著提高系统的可靠性和稳定性。

## 🚀 主要特性

### ✅ 智能重试策略
- **指数退避算法**: 重试间隔逐渐增加，避免对服务器造成压力
- **随机抖动**: 防止多个请求同时重试，分散负载
- **错误分类**: 区分可重试和不可重试的错误类型
- **统计记录**: 详细的重试统计信息

### 🎯 支持的重试场景
- **网络连接错误**: 网络超时、连接中断
- **服务器错误**: 5xx 状态码错误
- **频率限制**: 429 Too Many Requests
- **临时API错误**: 临时性的API服务问题
- **响应解析错误**: JSON解析失败
- **编码错误**: UTF-8编码/解码错误（已修复）

### 🚫 不重试的错误类型
- **认证错误**: 401 Unauthorized
- **请求格式错误**: 400 Bad Request
- **配额超出**: 403 Quota Exceeded

## ⚙️ 配置说明

### 配置文件 (`config.json`)

```json
{
  "retry": {
    "max_retries": 3,                    // 最大重试次数
    "base_delay": 1.0,                   // 基础延迟时间（秒）
    "max_delay": 30.0,                   // 最大延迟时间（秒）
    "exponential_base": 2,               // 指数退避基数
    "jitter_factor": 0.25,               // 随机抖动因子
    "retry_on_network_error": true,      // 网络错误时重试
    "retry_on_server_error": true,       // 服务器错误时重试
    "retry_on_rate_limit": true,         // 频率限制时重试
    "retry_on_timeout": true,            // 超时时重试
    "non_retryable_errors": [            // 不可重试的错误类型
      "auth", 
      "invalid_request", 
      "quota_exceeded"
    ]
  }
}
```

### 重试延迟计算公式

```
延迟时间 = min(基础延迟 × 指数基数^重试次数, 最大延迟) + 随机抖动
随机抖动 = 延迟时间 × 抖动因子 × (-1 到 1 的随机数)
```

## 📊 使用示例

### 基本用法

```python
from LLMTool import LLMApiClient

# 创建客户端（自动使用配置文件中的重试设置）
client = LLMApiClient()

# 发送请求（自动重试）
messages = [{"role": "user", "content": "你好"}]
response = client.call(messages)

if response:
    print("✅ 请求成功")
else:
    print("❌ 所有重试均失败")
```

### 自定义重试配置

```python
# 创建自定义配置的客户端
client = LLMApiClient()

# 临时修改重试配置
client.retry_max_retries = 5
client.retry_base_delay = 2.0
client.retry_max_delay = 60.0

# 发送请求
response = client.call(messages)
```

### 批量调用（自动重试）

```python
# 批量调用，每个请求都有独立的重试机制
message_batches = [
    [{"role": "user", "content": "请求1"}],
    [{"role": "user", "content": "请求2"}],
    [{"role": "user", "content": "请求3"}]
]

results = client.batch_call(message_batches)
successful = sum(1 for r in results if r is not None)
print(f"成功: {successful}/{len(message_batches)}")
```

## 📈 重试统计信息

### 日志输出示例

```
ℹ️ 发送LLM请求 (尝试 1/3)
⚠️ LLM请求失败 (错误类型: network)，1.2秒后重试...
ℹ️ 发送LLM请求 (尝试 2/3)
⚠️ LLM请求失败 (错误类型: network)，2.8秒后重试...
ℹ️ 发送LLM请求 (尝试 3/3)
✅ LLM请求成功 (第3次尝试)
ℹ️ 重试统计: 总尝试3次, 网络错误2次, API错误0次, 解析错误0次, 频率限制0次, 服务器错误0次, 最终成功
```

### 统计字段说明

| 字段 | 说明 |
|------|------|
| `total_attempts` | 总尝试次数 |
| `network_errors` | 网络错误次数 |
| `api_errors` | API错误次数 |
| `parse_errors` | 解析错误次数 |
| `rate_limit_errors` | 频率限制错误次数 |
| `server_errors` | 服务器错误次数 |
| `success` | 最终是否成功 |

## 🧪 测试重试机制

### 运行测试脚本

```bash
python test_retry.py
```

### 测试内容

1. **配置显示**: 显示当前重试配置
2. **延迟计算**: 测试重试延迟计算算法
3. **错误分类**: 验证错误分类逻辑
4. **实际调用**: 测试真实的API调用重试

### 测试输出示例

```
🔄 LLM重试机制测试工具 - 开始综合测试
==================================================
🔄 配置信息 - 显示当前重试相关配置
ℹ️ API配置:
  url: https://api.rcouyi.com/v1/chat/completions
  key: sk-rJeYV6e...***
  default_model: gpt-5-mini
  timeout: 30
  max_retries: 3
ℹ️ 重试配置:
  max_retries: 3
  base_delay: 1.0
  max_delay: 30.0
  exponential_base: 2
  jitter_factor: 0.25
  non_retryable_errors: ['auth', 'invalid_request', 'quota_exceeded']

==================================================
🔄 延迟计算测试 - 测试重试延迟计算算法
ℹ️ 重试延迟计算示例:
  第1次重试: 0.87秒
  第2次重试: 1.93秒
  第3次重试: 4.21秒
  第4次重试: 7.82秒
  第5次重试: 15.34秒

==================================================
🔄 错误分类测试 - 测试重试策略
ℹ️ 错误类型重试策略:
  network: ✅ 可重试
  api: ✅ 可重试
  parse: ✅ 可重试
  rate_limit: ✅ 可重试
  server_error: ✅ 可重试
  auth: ❌ 不重试
  invalid_request: ❌ 不重试
  quota_exceeded: ❌ 不重试
```

## 🎛️ 高级配置

### 针对不同环境的配置建议

#### 开发环境
```json
{
  "retry": {
    "max_retries": 2,
    "base_delay": 0.5,
    "max_delay": 10.0
  }
}
```

#### 生产环境
```json
{
  "retry": {
    "max_retries": 5,
    "base_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2,
    "jitter_factor": 0.3
  }
}
```

#### 高并发场景
```json
{
  "retry": {
    "max_retries": 3,
    "base_delay": 2.0,
    "max_delay": 30.0,
    "jitter_factor": 0.5
  }
}
```

### 性能优化建议

1. **合理设置重试次数**: 避免过多重试导致响应时间过长
2. **调整延迟参数**: 根据API服务特性调整延迟时间
3. **监控重试统计**: 关注重试率，优化配置
4. **错误类型分析**: 根据常见错误类型调整重试策略

## 🔍 错误排查

### 常见问题

#### 1. 重试次数过多
**症状**: 请求响应时间很长
**解决**: 降低 `max_retries` 或调整延迟参数

#### 2. 重试无效果
**症状**: 仍然频繁失败
**检查**: 
- API密钥是否正确
- 网络连接是否稳定
- 是否遇到了不可重试的错误

#### 3. 配置不生效
**症状**: 重试行为没有改变
**解决**: 
- 检查 `config.json` 格式是否正确
- 确认配置文件路径
- 重启应用程序

### 调试方法

```python
# 启用详细日志
from common_utils import LogUtils

# 查看重试配置
client = LLMApiClient()
print(f"重试配置: {client.get_config()}")

# 手动测试重试延迟计算
for i in range(3):
    delay = client._calculate_retry_delay(i, 1.0, 30.0)
    print(f"重试 {i+1}: {delay:.2f}秒")
```

## 📚 最佳实践

### 1. 合理配置重试参数
- 根据API服务的特性调整参数
- 考虑用户体验和资源消耗的平衡
- 定期监控和调整配置

### 2. 错误处理
```python
try:
    response = client.call(messages)
    if response:
        # 处理成功响应
        process_response(response)
    else:
        # 处理重试失败情况
        handle_failure()
except Exception as e:
    # 处理异常
    log_error(e)
```

### 3. 监控和告警
- 监控重试率和成功率
- 设置异常告警
- 定期分析错误类型分布

### 4. 性能考虑
- 在高并发场景下，合理设置抖动因子
- 避免所有请求同时重试
- 考虑使用连接池

---

## 🎯 总结

智能重试机制为 PromptSplit 系统提供了强大的容错能力：

- **🛡️ 提高可靠性**: 自动处理临时性错误
- **⚡ 优化性能**: 智能延迟策略减少服务器压力
- **📊 详细统计**: 全面的重试统计信息
- **🔧 灵活配置**: 支持多种场景的配置需求

通过合理配置和使用重试机制，您的 LLM API 调用将变得更加稳定和可靠！ 