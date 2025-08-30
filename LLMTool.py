import json
import http.client
from typing import List, Optional

from common_utils import JSONProcessor


class LLMApiClient:
    def __init__(self, api_key=None, api_url=None):
        # 移除硬编码的默认key，让用户必须明确指定
        self.api_key = '15e0122b-bf1e-415f-873b-1cb6b39bb612'
        # self.api_url = api_url or 'https://api.rcouyi.com/v1/chat/completions'
        self.api_url = api_url or 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'
        
        # 解析URL
        if '://' in self.api_url:
            self.host = self.api_url.split('://')[1].split('/')[0]
            self.path = '/' + '/'.join(self.api_url.split('://')[1].split('/')[1:])
        else:
            self.host = self.api_url
            self.path = '/v3/chat/completions'
    
    def call(self, messages, model=None, max_tokens=8000):
        # 检查API key是否已设置
        if not self.api_key:
            print('错误: 未设置API Key，请先配置API Key')
            return None
            
        # 使用默认模型
        # model = model or 'gpt-5-mini'
        model = model or 'doubao-seed-1-6-250615'
        
        # 构建请求数据
        payload = {
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens
        }
        
        # 发送请求
        conn = http.client.HTTPSConnection(self.host)
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            conn.request('POST', self.path, json.dumps(payload), headers)
            res = conn.getresponse()
            data = res.read().decode('utf-8')
            
            if res.status == 200:
                response_json = json.loads(data)
                return response_json['choices'][0]['message']['content']
            else:
                print(f'请求失败: {res.status} - {data}')
                return None
                
        except Exception as e:
            print(f'请求异常: {e}')
            return None
        finally:
            conn.close()

    def extract_json_string(self, text: str) -> str:
        """
        从文本中提取JSON字符串（使用公共工具）

        Args:
            text: 包含JSON的文本

        Returns:
            提取的JSON字符串
        """
        if not text:
            return ""

        # 使用公共JSON处理器
        result = JSONProcessor.extract_json_string(text)

        # 如果公共工具未找到，使用原有的更精确的方法
        if result == text:  # 表示未找到JSON
            return self._extract_json_precise(text)

        return result

    def _extract_json_precise(self, text: str) -> Optional[str]:
        """
        精确的JSON提取方法（保留原有逻辑作为后备）

        Args:
            text: 包含JSON的文本

        Returns:
            提取的JSON字符串或None
        """
        start_index = -1
        brace_count = 0

        for i, char in enumerate(text):
            if char == '{':
                if start_index == -1:
                    start_index = i
                brace_count += 1
            elif char == '}':
                if start_index != -1:
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = text[start_index: i + 1]
                        try:
                            json.loads(json_str)
                            return json_str
                        except json.JSONDecodeError:
                            start_index = -1

        return None

    def extract_variables_from_json(self, json_str: str) -> List[str]:
        """
        从JSON字符串中提取变量名（使用公共工具）

        Args:
            json_str: JSON字符串

        Returns:
            变量名列表
        """
        return JSONProcessor.extract_variables_from_json(json_str)

# 便捷函数
def create_client(api_key=None, api_url=None):
    return LLMApiClient(api_key, api_url)


if __name__ == '__main__':
    client = create_client()
    res = client.call([{"role": "user", "content": "你好"}])
    print(res)