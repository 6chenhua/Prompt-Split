"""
API连接调试工具
帮助诊断和解决API连接问题
"""

import json
import http.client
import ssl
from urllib.parse import urlparse


def test_api_detailed(api_key: str, base_url: str, model: str):
    """详细的API测试"""
    print("🔍 开始详细API测试...")
    print(f"📍 API URL: {base_url}")
    print(f"🤖 模型: {model}")
    print(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]}")
    print("-" * 50)
    
    # 解析URL
    parsed = urlparse(base_url)
    host = parsed.netloc
    
    # 根据URL判断API类型和路径
    if "anthropic" in base_url.lower():
        path = "/v1/messages"
        api_type = "Anthropic"
        payload = {
            "model": model,
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "请回复'测试成功'"}]
        }
    else:
        # OpenAI兼容格式
        path = "/v1/chat/completions"
        api_type = "OpenAI兼容"
        payload = {
            "model": model,
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "请回复'测试成功'"}]
        }
    
    print(f"📡 API类型: {api_type}")
    print(f"🛣️ 请求路径: {path}")
    print(f"📦 请求载荷: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print("-" * 50)
    
    try:
        # 准备请求
        payload_str = json.dumps(payload, ensure_ascii=False)
        payload_bytes = payload_str.encode('utf-8')
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {api_key}",
            "Content-Length": str(len(payload_bytes))
        }
        
        print("📨 请求头信息:")
        for key, value in headers.items():
            if key == "Authorization":
                print(f"  {key}: Bearer {api_key[:8]}...{api_key[-4:]}")
            else:
                print(f"  {key}: {value}")
        print("-" * 50)
        
        # 创建连接
        print(f"🔗 连接到: {host}")
        conn = http.client.HTTPSConnection(host, timeout=30)
        
        # 发送请求
        print(f"📤 发送POST请求到: {path}")
        conn.request("POST", path, body=payload_bytes, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
        conn.close()
        
        print(f"📥 响应状态: {response.status} {response.reason}")
        print(f"📄 响应内容 (前500字符):")
        print(response_data[:500])
        
        if len(response_data) > 500:
            print("... (内容被截断)")
        
        print("-" * 50)
        
        # 分析响应
        if response.status == 200:
            try:
                response_json = json.loads(response_data)
                print("✅ JSON解析成功")
                print(f"📋 响应结构: {list(response_json.keys())}")
                
                # 尝试提取内容
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    choice = response_json["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"]
                        print(f"✅ 成功提取内容: {content}")
                        return True, f"API测试成功: {content}"
                    else:
                        print(f"❌ 响应格式不匹配，choice结构: {list(choice.keys())}")
                        return False, f"响应格式不匹配: {response_data}"
                else:
                    print(f"❌ 响应中没有choices字段")
                    return False, f"响应格式错误: {response_data}"
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                return False, f"JSON解析失败: {e}"
                
        else:
            print(f"❌ HTTP错误: {response.status}")
            return False, f"HTTP {response.status}: {response_data}"
            
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return False, f"连接异常: {e}"


def suggest_fixes(base_url: str, model: str, error_msg: str):
    """建议修复方案"""
    print("\n🔧 建议的修复方案:")
    print("-" * 30)
    
    if "404" in error_msg or "Not Found" in error_msg:
        print("1. ❌ API路径可能不正确")
        if "rcouyi" in base_url.lower():
            print("   🔧 尝试使用: https://api.rcouyi.com/v1/chat/completions")
        print("   💡 确认API服务商的正确路径")
        
    elif "401" in error_msg or "Unauthorized" in error_msg:
        print("1. ❌ API Key认证失败")
        print("   🔧 检查API Key是否正确且有效")
        print("   💡 确认API Key有使用该模型的权限")
        
    elif "400" in error_msg or "Bad Request" in error_msg:
        print("1. ❌ 请求格式错误")
        print("   🔧 检查模型名称是否正确")
        if model in ["gpt-5-mini", "gpt-5"]:
            print(f"   💡 模型 '{model}' 可能不存在，尝试:")
            print("      - gpt-3.5-turbo")
            print("      - gpt-4")
            print("      - gpt-4-turbo")
            
    elif "Connection" in error_msg:
        print("1. ❌ 网络连接问题")
        print("   🔧 检查网络连接")
        print("   💡 确认API服务器地址正确")
        print(f"   🌐 ping {urlparse(base_url).netloc}")
        
    elif "JSON" in error_msg:
        print("1. ❌ 响应格式问题")
        print("   🔧 API服务可能不完全兼容OpenAI格式")
        print("   💡 联系API服务商确认响应格式")
        
    print("\n📚 通用检查项:")
    print("1. 确认API Key有效且有余额")
    print("2. 确认模型名称正确")
    print("3. 确认API服务器URL正确")
    print("4. 检查网络连接和防火墙设置")


def main():
    """主函数"""
    print("🔧 API连接调试工具")
    print("=" * 50)
    
    # 从用户界面获取的配置
    api_key = input("请输入API Key: ").strip()
    base_url = input("请输入API Base URL (默认: https://api.rcouyi.com): ").strip()
    model = input("请输入模型名称 (默认: gpt-5-mini): ").strip()
    
    if not base_url:
        base_url = "https://api.rcouyi.com"
    if not model:
        model = "gpt-5-mini"
    
    print("\n" + "=" * 50)
    
    # 执行测试
    success, message = test_api_detailed(api_key, base_url, model)
    
    if not success:
        suggest_fixes(base_url, model, message)
    else:
        print("\n🎉 API测试成功！可以正常使用。")


if __name__ == "__main__":
    main() 