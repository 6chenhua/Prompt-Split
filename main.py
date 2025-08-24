import json
import re
import http.client
import ssl
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

# API配置
# 注意：在生产环境中，API密钥应通过环境变量或其他安全方式管理，而不是硬编码
DEFAULT_API_URL = "https://api.rcouyi.com/v1/chat/completions"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_CHUNK_SIZE = 300
DEFAULT_MAX_WORKERS = 10


class LLMApiClient:
    """封装对LLM API的调用逻辑"""

    def __init__(self, api_key: str, api_url: str = DEFAULT_API_URL):
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


def split_text_by_length(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> List[str]:
    """
    根据指定长度切割文本，确保在换行符处切割以保持完整性。

    Args:
        text (str): 待切割的原始文本。
        chunk_size (int): 每段文本的最小长度。

    Returns:
        List[str]: 包含切割后文本段的列表。
    """
    if not isinstance(text, str):
        raise TypeError("输入必须是字符串类型。")
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正数。")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length and text[end] != '\n':
            next_newline = text.find('\n', end)
            end = next_newline + 1 if next_newline != -1 else text_length
        chunks.append(text[start:end])
        start = end

    return [chunk for chunk in chunks if chunk.strip()]


def extract_variables_from_json(json_str: str) -> List[str]:
    """
    从LLM返回的JSON字符串中提取变量名。

    Args:
        json_str (str): LLM响应的JSON字符串。

    Returns:
        List[str]: 提取到的变量名列表。
    """
    if not json_str:
        return []

    match = re.search(r'\[.*?\]', json_str, re.DOTALL)
    if not match:
        return []

    try:
        json_array = json.loads(match.group(0))
        variable_names = [item['text'] for item in json_array if 'text' in item]
        return variable_names
    except json.JSONDecodeError as e:
        print(f"解析JSON失败: {e}")
        return []


def process_text_with_llm(
        text: str,
        api_key: str = 'sk-rJeYV6eGEYtqaEmpB2B4331bCdAa4474971d7a6236D4Fe07',
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        max_workers: int = DEFAULT_MAX_WORKERS
) -> List[str]:
    """
    主API函数，处理文本，调用LLM，并返回提取的变量名。

    Args:
        text (str): 待处理的原始文本。
        api_key (str): 用于调用API的密钥。
        sys_prompt_template (str): 包含占位符的系统提示模板。
        chunk_size (int): 文本分块大小。
        max_workers (int): 并发处理的线程数。

    Returns:
        List[str]: 从LLM响应中提取并去重后的所有变量名。
    """
    if not text:
        return []

    llm_client = LLMApiClient(api_key=api_key)
    chunks = split_text_by_length(text, chunk_size=chunk_size)
    sys_prompt_template = read_file('extract_var_v6.txt')

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                llm_client.call,
                messages=[{"role": "system", "content": sys_prompt_template.replace("{在此粘贴原文}", chunk)}],
                model=DEFAULT_MODEL
            ): i
            for i, chunk in enumerate(chunks)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                response_str = future.result()
                if response_str:
                    results[idx] = extract_variables_from_json(response_str)
                else:
                    results[idx] = []
            except Exception as e:
                print(f"处理任务 {idx} 失败: {e}")
                results[idx] = []

    # 保证结果按原始顺序排序
    ordered_results = [results.get(i, []) for i in range(len(chunks))]

    # 扁平化列表并去重
    all_variable_names = [name for sublist in ordered_results for name in sublist]
    return list(set(all_variable_names))


if __name__ == '__main__':
    # 示例用法
    # 假设 nl_prompt.txt 和 extract_var_v6.txt 存在于同一目录下
    def read_file(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


    try:
        user_text = read_file('nl_prompt.txt')

        extracted_variables = process_text_with_llm(
            text=user_text,
        )
        print("提取到的所有变量：")
        print(extracted_variables)

    except FileNotFoundError as e:
        print(f"文件未找到: {e}。请确保 'nl_prompt.txt' 和 'extract_var_v5.txt' 存在。")