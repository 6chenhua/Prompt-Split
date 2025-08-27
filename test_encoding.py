"""
测试中文编码问题的修复
验证LLM API能否正确处理包含中文字符的请求
"""

from common_utils import LogUtils
from LLMTool import LLMApiClient


def test_chinese_encoding():
    """测试中文编码"""
    LogUtils.log_step("中文编码测试", "测试包含中文字符的LLM请求")
    
    # 创建LLM客户端
    client = LLMApiClient()
    
    # 测试包含中文的请求
    test_cases = [
        {
            "name": "简单中文",
            "messages": [{"role": "user", "content": "你好，请介绍一下自己"}]
        },
        {
            "name": "复杂中文（包含变量抽取器等词汇）",
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一个专业的变量抽取器，能够从文本中识别和提取动态变量。"
                },
                {
                    "role": "user", 
                    "content": "请从以下文本中提取变量：这是一个包含{{用户名}}和{{产品名称}}的示例文本。"
                }
            ]
        },
        {
            "name": "包含特殊字符",
            "messages": [{"role": "user", "content": "测试特殊字符：「」【】〔〕《》〈〉『』''""…—～"}]
        },
        {
            "name": "长文本中文",
            "messages": [
                {
                    "role": "user", 
                    "content": "请分析以下业务需求：\n\n客户希望建立一个智能客服系统，能够自动回答用户的常见问题。系统需要支持多轮对话，理解用户意图，并提供准确的答案。同时，系统还需要具备学习能力，能够从历史对话中学习和改进。"
                }
            ]
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        LogUtils.log_info(f"测试 {i}/{len(test_cases)}: {test_case['name']}")
        
        try:
            response = client.call(test_case['messages'])
            
            if response:
                LogUtils.log_success(f"✅ {test_case['name']} - 成功")
                LogUtils.log_info(f"响应长度: {len(response)} 字符")
                LogUtils.log_info(f"响应预览: {response[:100]}...")
                success_count += 1
            else:
                LogUtils.log_error(f"❌ {test_case['name']} - 失败（返回空响应）")
                
        except Exception as e:
            LogUtils.log_error(f"❌ {test_case['name']} - 异常: {e}")
    
    LogUtils.log_info(f"测试完成: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)


def test_encoding_edge_cases():
    """测试编码边界情况"""
    LogUtils.log_step("编码边界测试", "测试各种编码边界情况")
    
    client = LLMApiClient()
    
    edge_cases = [
        {
            "name": "空字符串",
            "content": ""
        },
        {
            "name": "纯英文",
            "content": "Hello, this is a test message in English."
        },
        {
            "name": "纯中文",
            "content": "这是一条纯中文的测试消息。"
        },
        {
            "name": "中英混合",
            "content": "This is a mixed message with 中文 and English 内容。"
        },
        {
            "name": "包含emoji",
            "content": "测试emoji表情: 😀 🎉 ✅ ❌ 🔧"
        },
        {
            "name": "包含特殊符号",
            "content": "特殊符号测试: ©®™€£¥§¶†‡•…‰″‴‵‶‷‸‹›※‼‽⁇⁈⁉⁏⁐⁑⁒⁓⁔⁕⁖⁗⁘⁙⁚⁛⁜⁝⁞"
        },
        {
            "name": "长文本",
            "content": "很长的文本" * 100  # 300字符的重复文本
        }
    ]
    
    for case in edge_cases:
        if not case["content"]:  # 跳过空字符串测试
            continue
            
        LogUtils.log_info(f"测试: {case['name']}")
        
        # 测试编码
        try:
            import json
            test_payload = {"messages": [{"role": "user", "content": case["content"]}]}
            json_str = json.dumps(test_payload, ensure_ascii=False)
            encoded_bytes = json_str.encode('utf-8')
            
            LogUtils.log_success(f"编码成功 - {len(encoded_bytes)} 字节")
            
        except Exception as e:
            LogUtils.log_error(f"编码失败: {e}")


def test_payload_size():
    """测试不同大小的请求载荷"""
    LogUtils.log_step("载荷大小测试", "测试不同大小的请求是否能正确编码")
    
    import json
    
    sizes = [100, 500, 1000, 2000, 5000]  # 不同的字符数
    
    for size in sizes:
        content = "测试" * (size // 2)  # 每个"测试"是2个字符
        
        test_payload = {
            "model": "gpt-5-mini",
            "messages": [
                {"role": "user", "content": content}
            ]
        }
        
        try:
            json_str = json.dumps(test_payload, ensure_ascii=False)
            encoded_bytes = json_str.encode('utf-8')
            
            LogUtils.log_info(f"载荷大小 {size} 字符: JSON {len(json_str)} 字符, UTF-8 {len(encoded_bytes)} 字节")
            
        except Exception as e:
            LogUtils.log_error(f"载荷大小 {size} 编码失败: {e}")


def main():
    """主测试函数"""
    LogUtils.log_step("编码问题修复验证", "验证中文编码问题是否已解决")
    
    try:
        # 测试编码边界情况
        test_encoding_edge_cases()
        
        # 测试载荷大小
        test_payload_size()
        
        # 测试实际API调用
        if test_chinese_encoding():
            LogUtils.log_success("🎉 所有编码测试通过！")
        else:
            LogUtils.log_warning("⚠️ 部分编码测试失败")
            
    except Exception as e:
        LogUtils.log_error(f"测试过程中发生异常: {e}")


if __name__ == "__main__":
    main() 