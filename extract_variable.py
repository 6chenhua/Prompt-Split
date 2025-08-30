"""
变量提取模块
重构后版本：使用公共工具，消除重复代码
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

# 导入公共工具和重构后的LLM客户端
from common_utils import FileUtils, TextProcessor, JSONProcessor, LogUtils, ConfigUtils
from LLMTool import LLMApiClient


def call_llm(chunk: str, idx: int, llm_client: LLMApiClient = None, sys_prompt: str = None) -> tuple:
    """
    调用LLM处理单个分块
    
    Args:
        chunk: 文本块
        idx: 块索引
        llm_client: LLM客户端实例
        sys_prompt: 系统提示词
        
    Returns:
        (索引, 响应内容) 元组
    """
    LogUtils.log_info(f"开始处理文本块 {idx}")
    
    try:
        # 如果没有提供客户端，创建一个
        if llm_client is None:
            llm_client = LLMApiClient()
        
        # 如果没有提供系统提示，读取默认文件
        if sys_prompt is None:
            sys_prompt = FileUtils.read_file('my_prompts/extract_var_v6.txt')
            if not sys_prompt:
                LogUtils.log_error("无法读取系统提示文件 extract_var_v6.txt")
                return idx, ""
        
        # 构建消息
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": chunk},
        ]
        
        # 调用LLM
        content = llm_client.call(messages)
        
        if content:
            LogUtils.log_success(f"文本块 {idx} 处理成功")
            return idx, content
        else:
            LogUtils.log_warning(f"文本块 {idx} 返回空响应")
            return idx, ""
            
    except Exception as e:
        LogUtils.log_error(f"处理文本块 {idx} 失败: {e}")
        return idx, ""


def process_chunks_concurrently(chunks: List[str], max_workers: int = 5, 
                               llm_client: LLMApiClient = None) -> List[str]:
    """
    并发处理文本分块，从LLM回复中提取变量名
    
    Args:
        chunks: 文本块列表
        max_workers: 最大并发数
        llm_client: LLM客户端实例
        
    Returns:
        去重后的变量名列表
    """
    if not chunks:
        LogUtils.log_warning("没有文本块需要处理")
        return []
    
    # 使用配置或默认值
    config = ConfigUtils.get_config()
    max_workers = min(max_workers, config.get('max_workers', 5))
    
    # 如果没有提供客户端，创建一个
    if llm_client is None:
        llm_client = LLMApiClient()
    
    # 读取系统提示（一次读取，所有块共用）
    sys_prompt = FileUtils.read_file('my_prompts/extract_var_v6.txt')
    if not sys_prompt:
        LogUtils.log_error("无法读取系统提示文件")
        return []
    
    LogUtils.log_info(f"开始并发处理 {len(chunks)} 个文本块，并发数: {max_workers}")
    
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = [
            executor.submit(call_llm, chunk, i, llm_client, sys_prompt) 
            for i, chunk in enumerate(chunks)
        ]
        
        # 收集结果
        for future in as_completed(futures):
            idx, result_str = future.result()
            LogUtils.log_info(f"收到文本块 {idx} 的处理结果")
            
            if result_str:
                # 使用公共JSON处理器提取变量
                variables = JSONProcessor.extract_variables_from_json(result_str)
                results[idx] = variables
                LogUtils.log_success(f"文本块 {idx} 提取到 {len(variables)} 个变量")
            else:
                results[idx] = []
                LogUtils.log_warning(f"文本块 {idx} 未提取到变量")
    
    # 保证输出顺序和输入顺序一致
    ordered_results = [results.get(i, []) for i in range(len(chunks))]
    
    # 扁平化列表并去重
    all_variable_names = [name for sublist in ordered_results for name in sublist]
    unique_variables = list(set(all_variable_names))
    
    LogUtils.log_success(f"并发处理完成，共提取到 {len(unique_variables)} 个唯一变量")
    return unique_variables


def post_process(nl_with_var: str, llm_client: LLMApiClient = None) -> str:
    """
    后处理变量标记文本
    
    Args:
        nl_with_var: 标记了变量的文本
        llm_client: LLM客户端实例
        
    Returns:
        处理后的文本
    """
    LogUtils.log_info("开始后处理变量标记")
    
    try:
        # 读取后处理提示词
        prompt_template = FileUtils.read_file('my_prompts/post_process_variable_v2.txt')
        if not prompt_template:
            LogUtils.log_error("无法读取后处理提示文件")
            return nl_with_var
        
        # 替换占位符
        prompt = prompt_template.replace("{{prompt_with_var}}", nl_with_var)
        
        # 如果没有提供客户端，创建一个
        if llm_client is None:
            llm_client = LLMApiClient()
        
        # 调用LLM
        messages = [{"role": "system", "content": prompt}]
        res = llm_client.call(messages)
        
        if not res:
            LogUtils.log_warning("后处理返回空结果，使用原文本")
            return nl_with_var
        
        # 尝试多种方式提取和解析JSON
        processed_text = nl_with_var
        
        # 方法1: 使用LLM客户端的JSON提取
        json_str = llm_client.extract_json_string(res)
        if json_str:
            try:
                processed_data = json.loads(json_str)
                if 'cleaned_text' in processed_data:
                    processed_text = processed_data['cleaned_text']
                    LogUtils.log_success("变量后处理完成")
                    return processed_text
            except json.JSONDecodeError as e:
                LogUtils.log_warning(f"方法1 JSON解析失败: {e}")
        
        # 方法2: 直接尝试解析整个响应
        try:
            processed_data = json.loads(res)
            if 'cleaned_text' in processed_data:
                processed_text = processed_data['cleaned_text']
                LogUtils.log_success("变量后处理完成")
                return processed_text
        except json.JSONDecodeError:
            LogUtils.log_info("方法2 JSON解析失败，尝试其他方法")
        
        # 方法3: 使用正则表达式提取JSON块
        import re
        json_pattern = r'\{[^{}]*"cleaned_text"[^{}]*\}'
        matches = re.findall(json_pattern, res, re.DOTALL)
        for match in matches:
            try:
                processed_data = json.loads(match)
                if 'cleaned_text' in processed_data:
                    processed_text = processed_data['cleaned_text']
                    LogUtils.log_success("变量后处理完成")
                    return processed_text
            except json.JSONDecodeError:
                continue
        
        # 如果所有方法都失败，使用原文本
        LogUtils.log_warning("所有JSON解析方法都失败，使用原文本")
        LogUtils.log_success("变量后处理完成")
        return processed_text
            
    except Exception as e:
        LogUtils.log_error(f"后处理失败: {e}")
        return nl_with_var


def extract_variables_from_text(text: str, chunk_size: int = None, max_workers: int = None) -> Dict[str, Any]:
    """
    从文本中提取变量的完整流程
    
    Args:
        text: 原始文本
        chunk_size: 文本分块大小
        max_workers: 最大并发数
        
    Returns:
        包含变量和处理结果的字典
    """
    LogUtils.log_step("变量提取", "开始完整的变量提取流程")
    
    if not text or not text.strip():
        LogUtils.log_error("输入文本为空")
        return {"error": "输入文本为空"}
    
    try:
        # 获取配置
        config = ConfigUtils.get_config()
        chunk_size = chunk_size or config.get('chunk_size', 500)
        max_workers = max_workers or config.get('max_workers', 5)
        
        # 使用公共文本处理器分割文本
        LogUtils.log_info(f"使用分块大小: {chunk_size}")
        chunks = TextProcessor.split_text_by_length(text, chunk_size)
        LogUtils.log_info(f"文本已分割为 {len(chunks)} 个块")
        
        # 创建LLM客户端
        llm_client = LLMApiClient()
        
        # 并发处理提取变量
        variables = process_chunks_concurrently(chunks, max_workers, llm_client)
        
        if not variables:
            LogUtils.log_warning("未提取到任何变量")
            return {
                "variables": [],
                "original_text": text,
                "text_with_vars": text,
                "chunks_count": len(chunks)
            }
        
        # 将变量标记到原文中
        LogUtils.log_info("开始标记变量到原文")
        text_with_vars = text
        for var in variables:
            text_with_vars = text_with_vars.replace(var, "{" + var + "}")
        
        # 后处理
        LogUtils.log_info("开始后处理")
        processed_text = post_process(text_with_vars, llm_client)
        
        # 清理文本
        processed_text = TextProcessor.clean_text(processed_text)
        
        result = {
            "variables": variables,
            "original_text": text,
            "text_with_vars": processed_text,
            "chunks_count": len(chunks),
            "stats": {
                "total_variables": len(variables),
                "chunks_processed": len(chunks),
                "chunk_size_used": chunk_size,
                "max_workers_used": max_workers
            }
        }
        
        LogUtils.log_success(f"变量提取完成，共提取 {len(variables)} 个变量")
        return result
        
    except Exception as e:
        LogUtils.log_error(f"变量提取流程失败: {e}")
        return {"error": str(e)}


def save_extraction_result(result: Dict[str, Any], output_dir: str = "output") -> bool:
    """
    保存变量提取结果
    
    Args:
        result: 提取结果
        output_dir: 输出目录
        
    Returns:
        是否保存成功
    """
    try:
        import os
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 保存变量列表
        variables_file = os.path.join(output_dir, "extracted_variables.json")
        variables_data = {
            "variables": result.get("variables", []),
            "stats": result.get("stats", {}),
            "timestamp": json.dumps(json.datetime.now().isoformat()) if hasattr(json, 'datetime') else None
        }
        
        if FileUtils.save_json(variables_file, variables_data):
            LogUtils.log_success(f"变量列表已保存到 {variables_file}")
        
        # 保存标记变量的文本
        text_file = os.path.join(output_dir, "text_with_variables.txt")
        if FileUtils.save_file(text_file, result.get("text_with_vars", "")):
            LogUtils.log_success(f"标记文本已保存到 {text_file}")
        
        return True
        
    except Exception as e:
        LogUtils.log_error(f"保存结果失败: {e}")
        return False


def main():
    """主函数 - 提供命令行接口"""
    import sys
    
    # 简单的命令行参数处理
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'nl_prompt.txt'
    
    LogUtils.log_step("变量提取工具", f"处理文件: {input_file}")
    
    # 检查输入文件
    if not FileUtils.read_file(input_file):
        LogUtils.log_error(f"无法读取输入文件: {input_file}")
        return
    
    # 读取文本
    text = FileUtils.read_file(input_file)
    LogUtils.log_info(f"已读取文本，长度: {len(text)} 字符")
    
    # 提取变量
    result = extract_variables_from_text(text)
    
    if "error" in result:
        LogUtils.log_error(f"提取失败: {result['error']}")
        return
    
    # 显示结果
    variables = result.get("variables", [])
    print(f"\n✅ 提取完成！共找到 {len(variables)} 个变量：")
    for i, var in enumerate(variables, 1):
        print(f"  {i}. {var}")
    
    # 保存结果
    if save_extraction_result(result):
        print(f"\n📁 结果已保存到 output/ 目录")
    
    print(f"\n📊 处理统计:")
    stats = result.get("stats", {})
    for key, value in stats.items():
        print(f"  - {key}: {value}")


if __name__ == '__main__':
    main()


