"""
主要API模块
重构后版本：去除重复代码，使用公共工具
"""

from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入公共工具和重构后的LLM客户端
from common_utils import FileUtils, TextProcessor, JSONProcessor, LogUtils, ConfigUtils
from LLMTool import LLMApiClient
from extract_variable import extract_variables_from_text


def process_text_with_llm(
    text: str,
    api_key: str = None,
    chunk_size: int = None,
    max_workers: int = None,
    config_file: str = None
) -> List[str]:
    """
    主API函数：处理文本并提取变量
    
    Args:
        text: 待处理的原始文本
        api_key: API密钥，如果不提供则从配置文件读取
        chunk_size: 文本分块大小，如果不提供则使用配置值
        max_workers: 并发处理的线程数，如果不提供则使用配置值
        config_file: 配置文件路径
        
    Returns:
        提取到的变量名列表
    """
    LogUtils.log_step("主API处理", "开始处理文本并提取变量")
    
    if not text or not text.strip():
        LogUtils.log_error("输入文本为空")
        return []
    
    try:
        # 使用重构后的变量提取模块
        result = extract_variables_from_text(text, chunk_size, max_workers)
        
        if "error" in result:
            LogUtils.log_error(f"处理失败: {result['error']}")
            return []
        
        variables = result.get("variables", [])
        LogUtils.log_success(f"API处理完成，提取到 {len(variables)} 个变量")
        return variables
        
    except Exception as e:
        LogUtils.log_error(f"API处理异常: {e}")
        return []


def process_text_with_custom_prompt(
    text: str,
    system_prompt: str,
    api_key: str = None,
    chunk_size: int = None,
    max_workers: int = None
) -> List[str]:
    """
    使用自定义系统提示处理文本
    
    Args:
        text: 待处理的原始文本
        system_prompt: 自定义系统提示
        api_key: API密钥
        chunk_size: 文本分块大小
        max_workers: 并发处理的线程数
        
    Returns:
        提取到的变量名列表
    """
    LogUtils.log_step("自定义提示处理", "使用自定义系统提示处理文本")
    
    if not text or not system_prompt:
        LogUtils.log_error("文本或系统提示为空")
        return []
    
    try:
        # 获取配置
        config = ConfigUtils.get_config()
        chunk_size = chunk_size or config.get('chunk_size', 500)
        max_workers = max_workers or config.get('max_workers', 5)
        
        # 创建LLM客户端
        llm_client = LLMApiClient(api_key)
        
        # 使用公共文本处理器分割文本
        chunks = TextProcessor.split_text_by_length(text, chunk_size)
        LogUtils.log_info(f"文本已分割为 {len(chunks)} 个块")
        
        # 并发处理
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _process_single_chunk,
                    chunk, system_prompt, llm_client
                ): i
                for i, chunk in enumerate(chunks)
            }
            
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    variables = future.result()
                    results[idx] = variables
                    LogUtils.log_info(f"块 {idx} 处理完成，提取到 {len(variables)} 个变量")
                except Exception as e:
                    LogUtils.log_error(f"处理块 {idx} 失败: {e}")
                    results[idx] = []
        
        # 整理结果
        ordered_results = [results.get(i, []) for i in range(len(chunks))]
        all_variables = [var for sublist in ordered_results for var in sublist]
        unique_variables = list(set(all_variables))
        
        LogUtils.log_success(f"自定义提示处理完成，提取到 {len(unique_variables)} 个唯一变量")
        return unique_variables
        
    except Exception as e:
        LogUtils.log_error(f"自定义提示处理异常: {e}")
        return []


def _process_single_chunk(chunk: str, system_prompt: str, llm_client: LLMApiClient) -> List[str]:
    """
    处理单个文本块
    
    Args:
        chunk: 文本块
        system_prompt: 系统提示
        llm_client: LLM客户端
        
    Returns:
        提取到的变量列表
    """
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chunk}
        ]
        
        response = llm_client.call(messages)
        if response:
            return JSONProcessor.extract_variables_from_json(response)
        else:
            return []
            
    except Exception as e:
        LogUtils.log_error(f"处理单个块失败: {e}")
        return []


def batch_process_texts(
    texts: List[str],
    api_key: str = None,
    chunk_size: int = None,
    max_workers: int = None
) -> List[List[str]]:
    """
    批量处理多个文本
    
    Args:
        texts: 文本列表
        api_key: API密钥
        chunk_size: 分块大小
        max_workers: 最大并发数
        
    Returns:
        每个文本的变量列表
    """
    LogUtils.log_step("批量处理", f"开始处理 {len(texts)} 个文本")
    
    results = []
    for i, text in enumerate(texts):
        LogUtils.log_info(f"处理第 {i+1}/{len(texts)} 个文本")
        variables = process_text_with_llm(text, api_key, chunk_size, max_workers)
        results.append(variables)
    
    LogUtils.log_success("批量处理完成")
    return results


def analyze_text_statistics(text: str) -> Dict[str, Any]:
    """
    分析文本的基本统计信息
    
    Args:
        text: 待分析的文本
        
    Returns:
        统计信息字典
    """
    if not text:
        return {"error": "文本为空"}
    
    # 基本统计
    stats = {
        "total_length": len(text),
        "total_lines": len(text.split('\n')),
        "total_words": len(text.split()),
        "total_paragraphs": len([p for p in text.split('\n\n') if p.strip()]),
    }
    
    # 使用配置估算分块信息
    config = ConfigUtils.get_config()
    chunk_size = config.get('chunk_size', 500)
    chunks = TextProcessor.split_text_by_length(text, chunk_size)
    
    stats.update({
        "estimated_chunks": len(chunks),
        "chunk_size_used": chunk_size,
        "average_chunk_length": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0
    })
    
    return stats


def validate_input_file(file_path: str) -> Dict[str, Any]:
    """
    验证输入文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        验证结果
    """
    result = {
        "valid": False,
        "file_exists": False,
        "readable": False,
        "content_length": 0,
        "error": None
    }
    
    try:
        # 检查文件是否存在
        if not FileUtils.read_file(file_path):
            result["error"] = f"文件 {file_path} 不存在或无法读取"
            return result
        
        result["file_exists"] = True
        
        # 读取文件内容
        content = FileUtils.read_file(file_path)
        if content:
            result["readable"] = True
            result["content_length"] = len(content)
            
            if len(content.strip()) > 0:
                result["valid"] = True
            else:
                result["error"] = "文件内容为空"
        else:
            result["error"] = "无法读取文件内容"
            
    except Exception as e:
        result["error"] = f"验证文件时出错: {e}"
    
    return result


def create_processing_report(
    input_file: str,
    variables: List[str],
    processing_time: float = None,
    statistics: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    创建处理报告
    
    Args:
        input_file: 输入文件路径
        variables: 提取到的变量
        processing_time: 处理时间（秒）
        statistics: 处理统计信息
        
    Returns:
        处理报告
    """
    import datetime
    
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "input_file": input_file,
        "total_variables": len(variables),
        "variables": variables,
        "processing_time_seconds": processing_time,
        "statistics": statistics or {}
    }
    
    # 添加性能评估
    if processing_time and statistics:
        chars_per_second = statistics.get("total_length", 0) / processing_time if processing_time > 0 else 0
        report["performance"] = {
            "characters_per_second": round(chars_per_second, 2),
            "variables_per_minute": round(len(variables) * 60 / processing_time, 2) if processing_time > 0 else 0
        }
    
    return report


def main():
    """主函数 - 提供命令行接口"""
    import sys
    import time
    
    # 简单的命令行参数处理
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'nl_prompt.txt'
    
    LogUtils.log_step("PromptSplit 主API", f"处理文件: {input_file}")
    
    # 验证输入文件
    validation = validate_input_file(input_file)
    if not validation["valid"]:
        LogUtils.log_error(f"文件验证失败: {validation['error']}")
        return
    
    LogUtils.log_success(f"文件验证通过，长度: {validation['content_length']} 字符")
    
    try:
        # 读取文本
        text = FileUtils.read_file(input_file)
        
        # 分析统计信息
        stats = analyze_text_statistics(text)
        LogUtils.log_info(f"文本统计: {stats['total_words']} 词，{stats['estimated_chunks']} 块")
        
        # 开始处理
        start_time = time.time()
        variables = process_text_with_llm(text)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # 显示结果
        print(f"\n✅ 处理完成！共提取到 {len(variables)} 个变量：")
        for i, var in enumerate(variables, 1):
            print(f"  {i:2d}. {var}")
        
        print(f"\n⏱️  处理时间: {processing_time:.2f} 秒")
        print(f"📊 处理速度: {stats['total_length'] / processing_time:.0f} 字符/秒")
        
        # 创建并保存报告
        report = create_processing_report(input_file, variables, processing_time, stats)
        if FileUtils.save_json("processing_report.json", report):
            LogUtils.log_success("处理报告已保存到 processing_report.json")
        
    except Exception as e:
        LogUtils.log_error(f"处理过程中出错: {e}")


if __name__ == '__main__':
    main()