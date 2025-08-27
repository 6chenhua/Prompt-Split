# 🔑 API配置指南

这份指南将帮助您快速配置AI提示词智能拆分工具的API设置。

## 📋 配置步骤

### 1. 获取API Key

#### 方案一：Claude (Anthropic) - 推荐
```
1. 访问：https://console.anthropic.com
2. 注册/登录账户
3. 进入API Keys页面
4. 创建新的API Key
5. 复制API Key (格式: sk-ant-api03-...)
```

#### 方案二：OpenAI GPT
```
1. 访问：https://platform.openai.com
2. 注册/登录账户
3. 进入API Keys页面
4. 创建新的API Key
5. 复制API Key (格式: sk-...)
```

### 2. 在工具中配置

1. **启动工具**
   ```bash
   python start_ui.py
   ```

2. **配置API**
   - 点击 "🔧 配置API" 按钮
   - 输入您的API Key
   - 选择对应的服务和模型
   - 点击 "🧪 测试连接" 验证
   - 点击 "💾 保存配置" 完成

3. **开始使用**
   - 输入需要拆分的提示词
   - 点击 "🚀 开始处理"

## 🔧 配置选项说明

### API服务器配置

| 服务商 | API Base URL | 推荐模型 |
|--------|--------------|----------|
| Anthropic | `https://api.anthropic.com` | claude-3-sonnet-20240229 |
| OpenAI | `https://api.openai.com` | gpt-4-turbo |
| 自定义 | 自定义URL | 根据服务商 |

### 模型选择指南

**Claude 模型：**
- `claude-3-sonnet-20240229` - 平衡性能和成本，推荐日常使用
- `claude-3-haiku-20240307` - 快速响应，适合简单任务

**OpenAI 模型：**
- `gpt-4-turbo` - 最新最强，处理复杂任务
- `gpt-4` - 稳定可靠
- `gpt-3.5-turbo` - 快速经济

## 🛡️ 安全说明

### API Key安全
- ✅ 仅在浏览器会话中使用
- ✅ 不会上传到服务器
- ✅ 不会永久存储在本地
- ⚠️ 关闭浏览器后需要重新输入

### 建议做法
1. **专用API Key**: 为此工具创建独立的API Key
2. **设置限额**: 在服务商后台设置使用限额
3. **定期轮换**: 定期更换API Key
4. **监控使用**: 关注API使用情况和费用

## 🔍 故障排除

### 常见问题

**Q: 提示"API Key未配置"？**
A: 请点击"🔧 配置API"按钮，输入有效的API Key

**Q: 测试连接失败？**
A: 检查：
- API Key是否正确
- 网络连接是否正常
- API服务器URL是否正确
- 模型名称是否支持

**Q: 处理过程中报错？**
A: 可能原因：
- API额度不足
- 网络中断
- 服务器故障
- 输入文本过长

**Q: 如何切换不同的AI服务？**
A: 重新配置API，更换API Key和服务器URL即可

### 错误代码

| 错误类型 | 可能原因 | 解决方案 |
|---------|----------|----------|
| 401 Unauthorized | API Key无效 | 检查并重新输入API Key |
| 429 Rate Limit | 请求过频 | 降低并发数，稍后重试 |
| 500 Server Error | 服务器问题 | 稍后重试或更换服务商 |
| Network Error | 网络问题 | 检查网络连接 |

## 💰 费用说明

### Claude (Anthropic)
- Sonnet: ~$3/M tokens input, ~$15/M tokens output
- Haiku: ~$0.25/M tokens input, ~$1.25/M tokens output

### OpenAI
- GPT-4 Turbo: ~$10/M tokens input, ~$30/M tokens output
- GPT-3.5 Turbo: ~$0.5/M tokens input, ~$1.5/M tokens output

### 预估使用量
- 1000字文本 ≈ 1000-1500 tokens
- 一般处理任务 ≈ $0.01-0.1 每次
- 复杂任务 ≈ $0.1-0.5 每次

**建议**: 先用小文本测试，了解实际费用后再处理大批量内容。

---

💡 **提示**: 配置完成后，您就可以开始使用AI提示词智能拆分工具了！ 