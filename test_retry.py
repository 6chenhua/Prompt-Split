"""
重试机制测试脚本
用于验证LLM API调用的重试机制是否正常工作
"""

import time
from common_utils import LogUtils, ConfigUtils
from LLMTool import LLMApiClient


def test_retry_mechanism():
    """测试重试机制"""
    LogUtils.log_step("重试机制测试", "开始测试LLM API重试功能")
    
    # 创建LLM客户端
    client = LLMApiClient()
    
    LogUtils.log_info(f"重试配置:")
    LogUtils.log_info(f"  - 最大重试次数: {client.retry_max_retries}")
    LogUtils.log_info(f"  - 基础延迟: {client.retry_base_delay}秒")
    LogUtils.log_info(f"  - 最大延迟: {client.retry_max_delay}秒")
    LogUtils.log_info(f"  - 指数基数: {client.retry_exponential_base}")
    LogUtils.log_info(f"  - 抖动因子: {client.retry_jitter_factor}")
    LogUtils.log_info(f"  - 不可重试错误: {client.non_retryable_errors}")
    
    # 测试正常调用
    LogUtils.log_step("测试1", "正常API调用")
    test_messages = [
        {"role": "user", "content": "请简单回答：1+1等于几？"}
    ]
    
    start_time = time.time()
    response = client.call(test_messages)
    end_time = time.time()
    
    if response:
        LogUtils.log_success(f"正常调用成功，用时: {end_time - start_time:.2f}秒")
        LogUtils.log_info(f"响应: {response[:100]}...")
    else:
        LogUtils.log_error("正常调用失败")
    
    # 测试连接测试功能
    LogUtils.log_step("测试2", "连接测试")
    if client.test_connection():
        LogUtils.log_success("连接测试通过")
    else:
        LogUtils.log_error("连接测试失败")
    
    # 测试批量调用
    LogUtils.log_step("测试3", "批量调用测试")
    message_batches = [
        [{"role": "user", "content": "2+2等于几？"}],
        [{"role": "user", "content": "3+3等于几？"}],
        [{"role": "user", "content": "4+4等于几？"}]
    ]
    
    start_time = time.time()
    results = client.batch_call(message_batches)
    end_time = time.time()
    
    successful = sum(1 for r in results if r is not None)
    LogUtils.log_info(f"批量调用完成，用时: {end_time - start_time:.2f}秒")
    LogUtils.log_info(f"成功: {successful}/{len(message_batches)}")


def test_retry_calculation():
    """测试重试延迟计算"""
    LogUtils.log_step("延迟计算测试", "测试重试延迟计算算法")
    
    client = LLMApiClient()
    
    LogUtils.log_info("重试延迟计算示例:")
    for attempt in range(5):
        delay = client._calculate_retry_delay(
            attempt, 
            client.retry_base_delay, 
            client.retry_max_delay
        )
        LogUtils.log_info(f"  第{attempt + 1}次重试: {delay:.2f}秒")


def test_error_classification():
    """测试错误分类"""
    LogUtils.log_step("错误分类测试", "测试重试策略")
    
    client = LLMApiClient()
    
    # 测试各种错误类型的重试策略
    error_types = [
        "network", "api", "parse", "rate_limit", "server_error",
        "auth", "invalid_request", "quota_exceeded"
    ]
    
    LogUtils.log_info("错误类型重试策略:")
    for error_type in error_types:
        should_retry = client._should_retry(error_type, 1)
        status = "✅ 可重试" if should_retry else "❌ 不重试"
        LogUtils.log_info(f"  {error_type}: {status}")


def show_config():
    """显示当前配置"""
    LogUtils.log_step("配置信息", "显示当前重试相关配置")
    
    config = ConfigUtils.get_config()
    
    LogUtils.log_info("API配置:")
    api_config = config.get('api', {})
    for key, value in api_config.items():
        if key == 'key':
            LogUtils.log_info(f"  {key}: {value[:10]}...***")
        else:
            LogUtils.log_info(f"  {key}: {value}")
    
    LogUtils.log_info("重试配置:")
    retry_config = config.get('retry', {})
    for key, value in retry_config.items():
        LogUtils.log_info(f"  {key}: {value}")


def main():
    """主函数"""
    LogUtils.log_step("LLM重试机制测试工具", "开始综合测试")
    
    try:
        # 显示配置信息
        show_config()
        
        # 测试重试计算
        test_retry_calculation()
        
        # 测试错误分类
        test_error_classification()
        
        # 测试实际API调用（如果配置正确）
        test_retry_mechanism()
        
        LogUtils.log_success("所有测试完成")
        
    except Exception as e:
        LogUtils.log_error(f"测试过程中出现异常: {e}")


if __name__ == "__main__":
    main() 