import json
import http.client
import ssl
from urllib.parse import urlparse
from typing import List, Optional

# API配置
# 注意：在生产环境中，API密钥应通过环境变量或其他安全方式管理，而不是硬编码
DEFAULT_API_URL = "https://api.rcouyi.com/v1/chat/completions"
DEFAULT_API_KEY = "sk-rJeYV6eGEYtqaEmpB2B4331bCdAa4474971d7a6236D4Fe07"
DEFAULT_MODEL = "gpt-5-mini"


class LLMApiClient:
    """封装对LLM API的调用逻辑"""

    def __init__(self, api_key: str = DEFAULT_API_KEY, api_url: str = DEFAULT_API_URL):
        self.api_key = api_key
        self.api_url = api_url
        parsed_url = urlparse(self.api_url)
        self.host = parsed_url.netloc
        self.path = parsed_url.path
        # 注意：忽略SSL验证在生产环境中非常不安全，仅用于测试
        self.ssl_context = ssl._create_unverified_context()

    def call(self, messages: List[dict], model: str = DEFAULT_MODEL) -> Optional[str]:
        """
        向LLM API发送请求并返回响应内容。

        Args:
            messages (List[dict]): 包含系统和用户消息的列表。
            model (str): 要使用的LLM模型名称。

        Returns:
            Optional[str]: LLM响应内容，如果请求失败则返回None。
        """
        try:
            payload = {
                "model": model,
                "messages": messages
            }
            payload_str = json.dumps(payload)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Length": str(len(payload_str))
            }

            conn = http.client.HTTPSConnection(self.host, context=self.ssl_context)
            conn.request("POST", self.path, body=payload_str, headers=headers)
            response = conn.getresponse()
            response_data = response.read().decode('utf-8')
            conn.close()

            if response.status != 200:
                print(f"API请求失败 (状态码: {response.status}): {response_data}")
                return None

            response_json = json.loads(response_data)
            return response_json["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"调用API时发生错误: {str(e)}")
            return None

    def extract_json_string(self, text):
        start_index = -1
        brace_count = 0

        # 遍历文本以找到 JSON 的起始位置
        for i, char in enumerate(text):
            if char == '{':
                if start_index == -1:
                    start_index = i
                brace_count += 1
            elif char == '}':
                if start_index != -1:
                    brace_count -= 1
                    # 如果大括号平衡，我们找到了完整的 JSON
                    if brace_count == 0:
                        json_str = text[start_index: i + 1]
                        # 验证提取的字符串是否为有效的 JSON
                        try:
                            json.loads(json_str)
                            return json_str
                        except json.JSONDecodeError:
                            # 如果无效，继续寻找下一个可能的 JSON
                            start_index = -1

        return None