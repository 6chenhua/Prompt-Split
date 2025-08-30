"""
LLM API 客户端工具
重构后版本：使用公共工具，提供统一的LLM调用接口
"""

import json
import http.client
import ssl
import time
import random
from urllib.parse import urlparse
from typing import List, Optional, Dict, Any

# 导入公共工具
from common_utils import JSONProcessor, LogUtils, ConfigUtils, ValidationUtils

# 默认配置
DEFAULT_CONFIG = {
    "api_url": "https://api.rcouyi.com/v1/chat/completions",
    "api_key": "sk-rJeYV6eGEYtqaEmpB2B4331bCdAa4474971d7a6236D4Fe07",
    "default_model": "gpt-5-mini",
    "timeout": 30,
    "max_retries": 3
}


class LLMApiClient:
    """
    统一的LLM API客户端
    - 集成公共工具
    - 配置管理
    - 错误处理和重试
    - 日志记录
    """

    def __init__(self, api_key: str = None, api_url: str = None, config_file: str = None):
        """
        初始化LLM API客户端
        
        Args:
            api_key: API密钥，如果不提供则从配置文件读取
            api_url: API地址，如果不提供则从配置文件读取
            config_file: 配置文件路径，默认为config.json
        """
        # 加载配置
        self.config = ConfigUtils.get_config(config_file or 'config.json')
        
        # 合并默认配置
        for key, value in DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = value
        
        # 设置API配置（优先使用传入参数）
        self.api_key = api_key or self.config.get('api_key', DEFAULT_CONFIG['api_key'])
        self.api_url = api_url or self.config.get('api_url', DEFAULT_CONFIG['api_url'])
        
        # 解析URL
        parsed_url = urlparse(self.api_url)
        self.host = parsed_url.netloc
        self.path = parsed_url.path
        
        # SSL配置（生产环境应使用安全的SSL验证）
        self.ssl_context = ssl._create_unverified_context()

        # 配置参数
        self.timeout = self.config.get('timeout', DEFAULT_CONFIG['timeout'])
        self.max_retries = self.config.get('max_retries', DEFAULT_CONFIG['max_retries'])
        self.default_model = self.config.get('default_model', DEFAULT_CONFIG['default_model'])
        
        # 重试配置
        retry_config = self.config.get('retry', {})
        self.retry_max_retries = retry_config.get('max_retries', self.max_retries)
        self.retry_base_delay = retry_config.get('base_delay', 1.0)
        self.retry_max_delay = retry_config.get('max_delay', 30.0)
        self.retry_exponential_base = retry_config.get('exponential_base', 2)
        self.retry_jitter_factor = retry_config.get('jitter_factor', 0.25)
        self.non_retryable_errors = retry_config.get('non_retryable_errors', ["auth", "invalid_request", "quota_exceeded"])
        
        LogUtils.log_info(f"LLM客户端初始化完成 - Host: {self.host}")

    def call(self, messages: List[dict], model: str = None, **kwargs) -> Optional[str]:
        """
        向LLM API发送请求并返回响应内容
        
        Args:
            messages: 包含系统和用户消息的列表
            model: 要使用的LLM模型名称，默认使用配置中的模型
            **kwargs: 其他API参数
            
        Returns:
            LLM响应内容，如果请求失败则返回None
        """
        # 参数验证
        if not self._validate_messages(messages):
            LogUtils.log_error("消息格式验证失败")
            return None
        
        # 使用默认模型
        model = model or self.default_model
        
        # 构建请求体
        payload = {
            "model": model,
            "messages": messages,
            **kwargs  # 支持其他参数如temperature, max_tokens等
        }
        
        # 智能重试机制
        return self._call_with_retry(payload)

    def _call_with_retry(self, payload: Dict[str, Any]) -> Optional[str]:
        """
        智能重试机制
        
        Args:
            payload: 请求载荷
            
        Returns:
            响应内容或None
        """
        retry_stats = {
            "attempts": 0,
            "network_errors": 0,
            "api_errors": 0,
            "parse_errors": 0,
            "rate_limit_errors": 0,
            "server_errors": 0,
            "success": False
        }
        
        for attempt in range(self.retry_max_retries):
            retry_stats["attempts"] += 1
            
            try:
                LogUtils.log_info(f"发送LLM请求 (尝试 {attempt + 1}/{self.retry_max_retries})")
                
                # 执行请求
                response, error_type = self._make_request_with_error_type(payload)
                
                if response:
                    retry_stats["success"] = True
                    LogUtils.log_success(f"LLM请求成功 (第{attempt + 1}次尝试)")
                    self._log_retry_stats(retry_stats)
                    return response
                
                # 记录错误类型
                if error_type == "network":
                    retry_stats["network_errors"] += 1
                elif error_type == "api":
                    retry_stats["api_errors"] += 1
                elif error_type == "parse":
                    retry_stats["parse_errors"] += 1
                elif error_type == "rate_limit":
                    retry_stats["rate_limit_errors"] += 1
                elif error_type == "server_error":
                    retry_stats["server_errors"] += 1
                
                # 检查是否应该重试
                if not self._should_retry(error_type, attempt + 1):
                    LogUtils.log_error(f"错误类型 '{error_type}' 不支持重试，停止尝试")
                    break
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < self.retry_max_retries - 1:
                    delay = self._calculate_retry_delay(attempt, self.retry_base_delay, self.retry_max_delay)
                    LogUtils.log_warning(f"LLM请求失败 (错误类型: {error_type})，{delay:.1f}秒后重试...")
                    time.sleep(delay)
                else:
                    LogUtils.log_error("已达到最大重试次数，停止尝试")
                    
            except Exception as e:
                retry_stats["network_errors"] += 1
                LogUtils.log_error(f"LLM请求异常 (尝试 {attempt + 1}/{self.retry_max_retries}): {e}")
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < self.retry_max_retries - 1:
                    delay = self._calculate_retry_delay(attempt, self.retry_base_delay, self.retry_max_delay)
                    LogUtils.log_warning(f"连接异常，{delay:.1f}秒后重试...")
                    time.sleep(delay)
        
        # 记录最终失败统计
        self._log_retry_stats(retry_stats)
        LogUtils.log_error("所有重试均失败")
        return None

    def _should_retry(self, error_type: str, attempt: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            error_type: 错误类型
            attempt: 当前尝试次数
            
        Returns:
            是否应该重试
        """
        # 检查是否为不可重试的错误类型
        if error_type in self.non_retryable_errors:
            return False
        
        # 超过最大重试次数
        if attempt >= self.retry_max_retries:
            return False
        
        return True

    def _calculate_retry_delay(self, attempt: int, base_delay: float, max_delay: float) -> float:
        """
        计算重试延迟时间（指数退避 + 随机抖动）
        
        Args:
            attempt: 当前尝试次数（从0开始）
            base_delay: 基础延迟时间
            max_delay: 最大延迟时间
            
        Returns:
            延迟时间（秒）
        """
        # 指数退避：exponential_base^attempt * base_delay
        exponential_delay = base_delay * (self.retry_exponential_base ** attempt)
        
        # 限制最大延迟
        exponential_delay = min(exponential_delay, max_delay)
        
        # 添加随机抖动
        jitter = exponential_delay * self.retry_jitter_factor * (2 * random.random() - 1)
        final_delay = exponential_delay + jitter
        
        # 确保延迟时间为正数
        return max(0.1, final_delay)

    def _log_retry_stats(self, stats: Dict[str, Any]) -> None:
        """
        记录重试统计信息
        
        Args:
            stats: 重试统计数据
        """
        if stats["attempts"] > 1:
            LogUtils.log_info(f"重试统计: 总尝试{stats['attempts']}次, "
                            f"网络错误{stats['network_errors']}次, "
                            f"API错误{stats['api_errors']}次, "
                            f"解析错误{stats['parse_errors']}次, "
                            f"频率限制{stats['rate_limit_errors']}次, "
                            f"服务器错误{stats['server_errors']}次, "
                            f"最终{'成功' if stats['success'] else '失败'}")

    def _make_request_with_error_type(self, payload: Dict[str, Any]) -> tuple[Optional[str], str]:
        """
        执行HTTP请求并返回错误类型

        Args:
            payload: 请求载荷

        Returns:
            (响应内容或None, 错误类型)
        """
        try:
            payload_str = json.dumps(payload, ensure_ascii=False)
            payload_bytes = payload_str.encode('utf-8')
            
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self.api_key}",
                # "Content-Length": str(len(payload_bytes))
            }
            
            # 创建连接
            conn = http.client.HTTPSConnection(
                self.host, 
                # context=self.ssl_context,
                # timeout=self.timeout
            )
            
            # 发送请求（使用UTF-8编码的字节）
            conn.request("POST", self.path, body=payload_bytes, headers=headers)
            response = conn.getresponse()
            response_data = response.read().decode('utf-8')
            conn.close()
            
            # 检查响应状态并分类错误
            if response.status == 200:
                # 解析响应
                try:
                    response_json = json.loads(response_data)
                    content = response_json["choices"][0]["message"]["content"].strip()
                    return content, "success"
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    LogUtils.log_error(f"响应解析失败: {e}")
                    return None, "parse"
            
            # 根据HTTP状态码分类错误
            elif response.status == 401:
                LogUtils.log_error(f"认证失败 (401): {response_data}")
                return None, "auth"
            elif response.status == 400:
                LogUtils.log_error(f"请求无效 (400): {response_data}")
                return None, "invalid_request"
            elif response.status == 429:
                LogUtils.log_error(f"请求频率限制 (429): {response_data}")
                return None, "rate_limit"
            elif response.status == 403:
                LogUtils.log_error(f"配额超出 (403): {response_data}")
                return None, "quota_exceeded"
            elif 500 <= response.status < 600:
                LogUtils.log_error(f"服务器错误 ({response.status}): {response_data}")
                return None, "server_error"
            else:
                LogUtils.log_error(f"API请求失败 ({response.status}): {response_data}")
                return None, "api"
                
        except (ConnectionError, TimeoutError, OSError) as e:
            LogUtils.log_error(f"网络连接失败: {e}")
            return None, "network"
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            LogUtils.log_error(f"编码错误: {e}")
            return None, "encoding"
        except Exception as e:
            LogUtils.log_error(f"请求执行失败: {e}")
            return None, "unknown"

    def _make_request(self, payload: Dict[str, Any]) -> Optional[str]:
        """
        执行实际的HTTP请求
        
        Args:
            payload: 请求载荷
            
        Returns:
            响应内容或None
        """
        try:
            payload_str = json.dumps(payload, ensure_ascii=False)
            payload_bytes = payload_str.encode('utf-8')

            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Length": str(len(payload_bytes))
            }
            
            # 创建连接
            conn = http.client.HTTPSConnection(
                self.host, 
                context=self.ssl_context,
                timeout=self.timeout
            )
            
            # 发送请求（使用UTF-8编码的字节）
            conn.request("POST", self.path, body=payload_bytes, headers=headers)
            response = conn.getresponse()
            response_data = response.read().decode('utf-8')
            conn.close()

            # 检查响应状态
            if response.status != 200:
                LogUtils.log_error(f"API请求失败 (状态码: {response.status}): {response_data}")
                return None

            # 解析响应
            try:
                response_json = json.loads(response_data)
                return response_json["choices"][0]["message"]["content"].strip()
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                LogUtils.log_error(f"响应解析失败: {e}")
                return None

        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            LogUtils.log_error(f"编码错误: {e}")
            return None
        except Exception as e:
            LogUtils.log_error(f"请求执行失败: {e}")
            return None

    def _validate_messages(self, messages: List[dict]) -> bool:
        """
        验证消息格式
        
        Args:
            messages: 消息列表
            
        Returns:
            是否有效
        """
        if not isinstance(messages, list) or len(messages) == 0:
            return False
        
        for msg in messages:
            if not isinstance(msg, dict):
                return False
            if 'role' not in msg or 'content' not in msg:
                return False
            if msg['role'] not in ['system', 'user', 'assistant']:
                return False
                
        return True

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

    def batch_call(self, message_batches: List[List[dict]], model: str = None, **kwargs) -> List[Optional[str]]:
        """
        批量调用LLM API
        
        Args:
            message_batches: 消息批次列表
            model: 模型名称
            **kwargs: 其他参数
            
        Returns:
            响应列表
        """
        results = []
        total = len(message_batches)
        
        LogUtils.log_info(f"开始批量调用，共 {total} 个请求")
        
        for i, messages in enumerate(message_batches):
            LogUtils.log_info(f"处理第 {i+1}/{total} 个请求")
            result = self.call(messages, model, **kwargs)
            results.append(result)
        
        successful = sum(1 for r in results if r is not None)
        LogUtils.log_success(f"批量调用完成，成功 {successful}/{total} 个请求")
        
        return results

    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        test_messages = [
            {"role": "user", "content": "Hello, this is a connection test."}
        ]
        
        LogUtils.log_info("测试API连接...")
        response = self.call(test_messages)
        
        if response:
            LogUtils.log_success("API连接测试成功")
            return True
        else:
            LogUtils.log_error("API连接测试失败")
            return False

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config.copy()

    def update_config(self, **kwargs) -> None:
        """
        更新配置
        
        Args:
            **kwargs: 要更新的配置项
        """
        for key, value in kwargs.items():
            if key in ['api_key', 'api_url', 'timeout', 'max_retries', 'default_model']:
                setattr(self, key, value)
                self.config[key] = value
                LogUtils.log_info(f"配置已更新: {key} = {value}")


# 便捷函数
def create_client(api_key: str = None, api_url: str = None, config_file: str = None) -> LLMApiClient:
    """
    创建LLM客户端的便捷函数
    
    Args:
        api_key: API密钥
        api_url: API地址
        config_file: 配置文件路径
        
    Returns:
        LLM客户端实例
    """
    return LLMApiClient(api_key, api_url, config_file)


# 向后兼容
def get_default_client() -> LLMApiClient:
    """获取默认配置的客户端"""
    return LLMApiClient()


if __name__ == "__main__":
    # 测试代码
    client = LLMApiClient()
    
    if client.test_connection():
        test_messages = [
            {"role": "user", "content": "请简单介绍一下Python编程语言"}
        ]
        
        response = client.call(test_messages)
        if response:
            print("✅ 测试成功！")
            print(f"响应: {response[:100]}...")
        else:
            print("❌ 测试失败")
    else:
        print("❌ 连接测试失败")