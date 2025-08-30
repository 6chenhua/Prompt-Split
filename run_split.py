import json
import os
import re
from typing import Dict, Any, List

# 导入公共工具
from common_utils import FileUtils, TextProcessor, LogUtils, ConfigUtils

# 导入现有的功能模块
from extract_variable import process_chunks_concurrently, post_process
from nl2cnlp import batch_transform_cnlp

# 导入first_split.py中的相关组件
from first_spilit import (
    generate_mermaid_messages, 
    split_messages, 
    sub_prompt_messages,
    generate_mermaid_prompt,
    split_subsystem_prompt_v3,
    generate_sub_prompt,
    llm_client
)

# 导入代码生成模块
from code_generator import CodeGenerator


class PromptSplitPipeline:
    """
    提示词拆分流程编排器
    重构后版本：使用公共工具，移除重复代码
    """
    
    def __init__(self, progress_callback=None):
        """
        初始化流水线
        
        Args:
            progress_callback: 进度回调函数，格式为 callback(step_name, progress, message)
        """
        self.config = ConfigUtils.get_config()
        self.progress_callback = progress_callback
        self.code_generator = CodeGenerator()  # 初始化代码生成器
        LogUtils.log_info("PromptSplit 流水线初始化完成")
    
    def _notify_progress(self, step_name: str, progress: int, message: str = "", result_data: Any = None):
        """通知进度更新"""
        if self.progress_callback:
            try:
                self.progress_callback(step_name, progress, message, result_data)
            except Exception as e:
                LogUtils.log_warning(f"进度回调执行失败: {e}")
    
    def read_file(self, file_path: str) -> str:
        """读取文件内容（使用公共工具）"""
        return FileUtils.read_file(file_path)
    
    def save_file(self, file_path: str, content: str) -> bool:
        """保存文件内容（使用公共工具）"""
        return FileUtils.save_file(file_path, content)
    
    def save_json(self, file_path: str, data: Dict) -> bool:
        """保存JSON数据（使用公共工具）"""
        return FileUtils.save_json(file_path, data)
    
    def step1_extract_variables(self, original_text: str) -> Dict[str, Any]:
        """
        第一步：提取变量（使用公共工具重构）
        """
        LogUtils.log_step("第一步：提取变量", "开始提取变量流程")
        self._notify_progress("输入验证", 0, "验证输入文本...")
        
        if not original_text or not original_text.strip():
            LogUtils.log_error("输入文本为空")
            return {"error": "输入文本为空"}
        
        self._notify_progress("输入验证", 100, f"输入文本长度: {len(original_text)} 字符")
        
        try:
            # 使用公共文本处理器分割文本
            self._notify_progress("文本分块", 0, "开始分割文本...")
            chunk_size = self.config.get('chunk_size', 500)
            chunks = TextProcessor.split_text_by_length(original_text, chunk_size)
            LogUtils.log_info(f"文本已切割为 {len(chunks)} 个块，块大小: {chunk_size}")
            
            # 立即传递文本分块结果
            chunk_result = {
                "chunk_count": len(chunks),
                "chunk_size": chunk_size,
                "total_chars": len(original_text),
                "chunks": chunks  # 传递所有分块，让UI分页显示
            }
            self._notify_progress("文本分块", 100, f"分割为 {len(chunks)} 个文本块", chunk_result)
            
            # 使用现有的并发处理函数提取变量
            self._notify_progress("提取变量", 0, "调用LLM提取变量...")
            variables = process_chunks_concurrently(chunks)
            LogUtils.log_success(f"提取到 {len(variables)} 个变量")
            
            # 立即传递变量提取结果
            variable_result = {
                "variables": variables,
                "total_count": len(variables)
            }
            self._notify_progress("提取变量", 100, f"提取到 {len(variables)} 个变量", variable_result)
            
            # 将变量标记到原文中
            self._notify_progress("后处理变量", 0, "开始变量后处理...")
            text_with_vars = original_text
            for var in variables:
                text_with_vars = text_with_vars.replace(var, "{" + var + "}")
            
            # 使用现有的后处理函数
            try:
                processed_text = post_process(text_with_vars)
                LogUtils.log_success("变量后处理完成")
            except Exception as e:
                LogUtils.log_warning(f"后处理失败，使用原始标记文本: {e}")
                processed_text = text_with_vars
            
            # 使用公共文本处理器清理文本
            processed_text = TextProcessor.clean_text(processed_text)
            
            # 立即传递后处理结果
            processing_result = {
                "processed_text": processed_text,
                "changes": [f"将 {len(variables)} 个变量标记为 {{变量名}} 格式"]
            }
            self._notify_progress("后处理变量", 100, "变量后处理完成", processing_result)
            
            result = {
                "variables": variables,
                "original_text": original_text,
                "text_with_vars": processed_text,
                "chunks_count": len(chunks),
                "stats": {
                    "chunk_size_used": chunk_size,
                    "total_variables": len(variables)
                }
            }
            
            LogUtils.log_success(f"第一步完成，提取到 {len(variables)} 个变量")
            return result
            
        except Exception as e:
            error_msg = f"变量提取失败: {e}"
            LogUtils.log_error(error_msg)
            return {"error": error_msg}
    
    def generate_mermaid_content(self, text: str) -> str:
        """
        生成Mermaid流程图
        修正first_split.py中gen_mermaid_content函数的逻辑
        """
        try:
            # 创建包含用户输入的消息列表
            messages = generate_mermaid_messages.copy()
            messages.append({"role": "user", "content": text})
            
            # 调用LLM生成流程分析和mermaid图
            response = llm_client.call(messages)
            
            # 从响应中提取mermaid图
            pattern = r"```mermaid(.*?)```"
            matches = re.findall(pattern, response, re.DOTALL)
            
            if matches:
                return matches[0].strip()
            else:
                print("⚠️ 未找到mermaid图，返回完整响应")
                return response
                
        except Exception as e:
            print(f"❌ 生成Mermaid图失败: {e}")
            return ""
    
    def split_to_subsystems(self, mermaid_content: str) -> Dict[str, Any]:
        """
        根据Mermaid图拆分为子系统
        """
        try:
            # 创建包含mermaid内容的消息列表
            messages = split_messages.copy()
            messages.append({"role": "user", "content": mermaid_content})
            
            # 调用LLM拆分子系统
            response = llm_client.call(messages)
            
            # 改进的JSON提取逻辑
            subsystems_data = self._extract_subsystems_json(response)
            if subsystems_data and "subsystems" in subsystems_data:
                return subsystems_data
            else:
                LogUtils.log_warning("未找到有效的子系统JSON数据")
                return {"subsystems": []}
            
        except Exception as e:
            LogUtils.log_error(f"子系统拆分失败: {e}")
            return {"subsystems": []}

    def _extract_subsystems_json(self, response: str) -> Dict[str, Any]:
        """
        改进的JSON提取方法，专门用于提取子系统数据
        
        Args:
            response: LLM的原始响应
            
        Returns:
            提取到的子系统数据字典
        """
        if not response:
            LogUtils.log_warning("LLM响应为空")
            return {}
        
        LogUtils.log_info("开始提取子系统JSON数据...")
        LogUtils.log_info(f"原始响应长度: {len(response)} 字符")
        LogUtils.log_info(f"响应预览: {response[:200]}...")
        
        # 尝试多种JSON提取策略
        strategies = [
            self._extract_json_strategy_1,  # 完整JSON块提取
            self._extract_json_strategy_2,  # 代码块提取
            self._extract_json_strategy_3,  # 逐行搜索
            self._extract_json_strategy_4   # 公共工具提取
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                LogUtils.log_info(f"尝试策略 {i}")
                result = strategy(response)
                if result and "subsystems" in result:
                    LogUtils.log_success(f"策略 {i} 成功提取JSON数据")
                    return result
                else:
                    LogUtils.log_warning(f"策略 {i} 未找到有效数据")
            except Exception as e:
                LogUtils.log_warning(f"策略 {i} 失败: {e}")
        
        LogUtils.log_error("所有JSON提取策略均失败")
        return {}

    def _extract_json_strategy_1(self, response: str) -> Dict[str, Any]:
        """策略1: 查找完整的JSON块（从第一个{到匹配的}）"""
        start_idx = response.find('{')
        if start_idx == -1:
            return {}
        
        brace_count = 0
        for i, char in enumerate(response[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = response[start_idx:i+1]
                    return json.loads(json_str)
        
        return {}

    def _extract_json_strategy_2(self, response: str) -> Dict[str, Any]:
        """策略2: 提取```json代码块中的JSON"""
        import re
        
        # 查找 ```json 代码块
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_block_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            return json.loads(match.group(1))
        
        return {}

    def _extract_json_strategy_3(self, response: str) -> Dict[str, Any]:
        """策略3: 逐行搜索，查找以{开头的行"""
        lines = response.split('\n')
        json_lines = []
        in_json = False
        brace_count = 0
        
        for line in lines:
            stripped = line.strip()
            if not in_json and stripped.startswith('{'):
                in_json = True
                json_lines = [line]
                brace_count = line.count('{') - line.count('}')
            elif in_json:
                json_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                if brace_count <= 0:
                    break
        
        if json_lines:
            json_str = '\n'.join(json_lines)
            return json.loads(json_str)
        
        return {}

    def _extract_json_strategy_4(self, response: str) -> Dict[str, Any]:
        """策略4: 使用公共工具的JSON提取"""
        from common_utils import JSONProcessor
        
        json_str = JSONProcessor.extract_json_string(response)
        if json_str and json_str != response:  # 确保提取到了JSON
            return json.loads(json_str)
        
        return {}

    def _extract_subprompts_json(self, response: str) -> Dict[str, Any]:
        """
        提取子提示词JSON数据（复用子系统提取逻辑）
        
        Args:
            response: LLM的原始响应
            
        Returns:
            提取到的子提示词数据字典
        """
        if not response:
            LogUtils.log_warning("LLM响应为空")
            return {}
        
        LogUtils.log_info("开始提取子提示词JSON数据...")
        LogUtils.log_info(f"原始响应长度: {len(response)} 字符")
        
        # 复用子系统的提取策略，但检查不同的字段
        strategies = [
            self._extract_json_strategy_1,
            self._extract_json_strategy_2,
            self._extract_json_strategy_3,
            self._extract_json_strategy_4
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                result = strategy(response)
                # 检查是否包含子提示词相关字段
                if result and ("subprompts" in result or "sub_prompts" in result):
                    LogUtils.log_success(f"策略 {i} 成功提取子提示词JSON数据")
                    # 统一字段名
                    if "sub_prompts" in result and "subprompts" not in result:
                        result["subprompts"] = result.pop("sub_prompts")
                    return result
                elif result:
                    LogUtils.log_warning(f"策略 {i} 提取到JSON但无子提示词字段")
            except Exception as e:
                LogUtils.log_warning(f"策略 {i} 失败: {e}")
        
        LogUtils.log_error("所有子提示词JSON提取策略均失败")
        return {}

    def _extract_subprompts_from_data(self, data: Any) -> list:
        """
        智能提取子提示词数据，处理各种可能的数据格式
        
        Args:
            data: 可能的数据格式（字典、列表或其他）
            
        Returns:
            子提示词列表
        """
        LogUtils.log_info("开始智能提取子提示词数据...")
        
        # 情况1: 数据为空或None
        if not data:
            LogUtils.log_warning("数据为空")
            return []
        
        # 情况2: 数据已经是列表
        if isinstance(data, list):
            LogUtils.log_info(f"数据已经是列表，包含 {len(data)} 项")
            return data
        
        # 情况3: 数据是字典
        if isinstance(data, dict):
            # 尝试多种可能的字段名
            possible_keys = ["subprompts", "sub_prompts", "prompts", "subPrompts"]
            
            for key in possible_keys:
                if key in data:
                    value = data[key]
                    LogUtils.log_info(f"找到字段 '{key}'，数据类型: {type(value)}")
                    
                    # 如果值是列表，直接返回
                    if isinstance(value, list):
                        LogUtils.log_success(f"成功提取 {len(value)} 个子提示词（字段: {key}）")
                        return value
                    
                    # 如果值是字典，尝试进一步提取
                    elif isinstance(value, dict):
                        LogUtils.log_info(f"字段 '{key}' 是字典，尝试进一步提取...")
                        return self._extract_subprompts_from_data(value)
            
            # 如果没有找到明确的字段，检查是否直接包含子提示词属性
            if all(key in data for key in ["name", "prompt"]):
                LogUtils.log_info("检测到单个子提示词对象")
                return [data]
        
        # 情况4: 其他数据类型
        LogUtils.log_warning(f"无法处理的数据类型: {type(data)}")
        LogUtils.log_warning(f"数据内容: {str(data)[:500]}")
        return []
    
    def generate_subprompts(self, original_text: str, subsystems_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为每个子系统生成对应的提示词
        """
        try:
            # 准备消息内容
            user_content = f"<<<初始提示词：\n{original_text}\n用户初始提示词结束>>>\n\n{json.dumps(subsystems_data, ensure_ascii=False)}"
            
            # 创建包含子系统信息的消息列表
            messages = sub_prompt_messages.copy()
            messages.append({"role": "user", "content": user_content})
            
            # 调用LLM生成子提示词
            response = llm_client.call(messages)
            
            # 改进的JSON提取逻辑（复用子系统的提取方法）
            subprompts_data = self._extract_subprompts_json(response)
            if subprompts_data and "subprompts" in subprompts_data:
                return subprompts_data
            else:
                LogUtils.log_warning("未找到有效的子提示词JSON数据")
                return {"subprompts": []}
                
        except Exception as e:
            LogUtils.log_error(f"子提示词生成失败: {e}")
            return {"subprompts": []}
    
    def step2_split_to_subprompts(self, text_with_vars: str) -> Dict[str, Any]:
        """
        第二步：拆分为子提示词
        按照first_split.py的完整逻辑：mermaid生成 → 子系统拆分 → 子提示词生成
        """
        LogUtils.log_step("第二步：拆分为子提示词", "按照完整流程：Mermaid生成 → 子系统拆分 → 子提示词生成")
        
        try:
            # 2.1 生成Mermaid流程图
            self._notify_progress("生成Mermaid图", 0, "开始生成Mermaid流程图...")
            LogUtils.log_info("🎨 步骤2.1：生成Mermaid流程图...")
            mermaid_content = self.generate_mermaid_content(text_with_vars)
            if not mermaid_content:
                LogUtils.log_error("Mermaid图生成失败")
                return {"error": "Mermaid图生成失败"}
            LogUtils.log_success("Mermaid图生成完成")
            # 立即传递Mermaid结果
            self._notify_progress("生成Mermaid图", 100, "Mermaid流程图生成完成", mermaid_content)
            
            # 2.2 拆分为子系统
            self._notify_progress("拆分子系统", 0, "开始拆分子系统...")
            LogUtils.log_info("🔧 步骤2.2：拆分为子系统...")
            subsystems_data = self.split_to_subsystems(mermaid_content)
            subsystems_count = len(subsystems_data.get("subsystems", []))
            if subsystems_count == 0:
                LogUtils.log_error("子系统拆分失败")
                return {"error": "子系统拆分失败"}
            LogUtils.log_success(f"拆分出 {subsystems_count} 个子系统")
            # 立即传递子系统结果
            self._notify_progress("拆分子系统", 100, f"拆分出 {subsystems_count} 个子系统", subsystems_data)
            
            # 2.3 生成子提示词
            self._notify_progress("生成子提示词", 0, "开始生成子系统对应的提示词...")
            LogUtils.log_info("📝 步骤2.3：生成子系统对应的提示词...")
            subprompts_data = self.generate_subprompts(text_with_vars, subsystems_data)
            subprompts_count = len(subprompts_data.get("subprompts", []))
            if subprompts_count == 0:
                LogUtils.log_error("子提示词生成失败")
                return {"error": "子提示词生成失败"}
            LogUtils.log_success(f"生成了 {subprompts_count} 个子提示词")
            # 立即传递子提示词结果
            self._notify_progress("生成子提示词", 100, f"生成了 {subprompts_count} 个子提示词", subprompts_data)
            
            # 整合结果
            result = {
                "method": "functional_split",
                "mermaid_content": mermaid_content,
                "subsystems": subsystems_data,
                "subprompts": subprompts_data,
                "processed_text": text_with_vars,
                "statistics": {
                    "subsystems_count": subsystems_count,
                    "subprompts_count": subprompts_count
                }
            }
            
            LogUtils.log_success("第二步完成")
            LogUtils.log_info(f"   - Mermaid图: 已生成")
            LogUtils.log_info(f"   - 子系统数量: {subsystems_count}")
            LogUtils.log_info(f"   - 子提示词数量: {subprompts_count}")
            
            return result
            
        except Exception as e:
            error_msg = f"拆分流程失败: {e}"
            LogUtils.log_error(error_msg)
            return {"error": error_msg}
    
    def step2_5_generate_code(self, subprompts_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        第2.5步：为子提示词生成代码（在第二步和第三步之间插入）
        """
        LogUtils.log_step("第2.5步：生成代码", "开始为子系统生成代码实现")
        self._notify_progress("代码生成", 0, "开始为子系统生成代码...")
        
        try:
            # 获取代码生成配置
            code_config = self.config.get('step2_5_code_generation', {})
            parallel_enabled = code_config.get('parallel_processing', True)
            max_workers = code_config.get('max_workers', 3)
            
            LogUtils.log_info(f"代码生成配置: 并行处理={parallel_enabled}, 最大线程数={max_workers}")
            
            # 使用代码生成器处理子提示词
            code_results = self.code_generator.batch_process_subprompts(
                subprompts_data, 
                parallel=parallel_enabled, 
                max_workers=max_workers
            )
            
            if "error" in code_results:
                LogUtils.log_error(f"代码生成失败: {code_results['error']}")
                return code_results
            
            # 获取统计信息
            summary = code_results.get("summary", {})
            total_count = summary.get("total_subprompts", 0)
            implementable_count = summary.get("implementable_count", 0)
            successful_count = summary.get("successful_count", 0)
            
            LogUtils.log_success(f"代码生成完成")
            LogUtils.log_info(f"   - 总子系统数: {total_count}")
            LogUtils.log_info(f"   - 可实现数: {implementable_count}")
            LogUtils.log_info(f"   - 成功生成代码数: {successful_count}")
            
            # 保存代码生成结果
            try:
                self.code_generator.save_code_generation_results(code_results)
                LogUtils.log_success("代码生成结果已保存")
            except Exception as e:
                LogUtils.log_warning(f"保存代码生成结果失败: {e}")
            
            # 立即传递代码生成结果
            self._notify_progress("代码生成", 100, f"成功生成 {successful_count}/{total_count} 个子系统的代码", code_results)
            
            return code_results
            
        except Exception as e:
            error_msg = f"代码生成流程失败: {e}"
            LogUtils.log_error(error_msg)
            return {"error": error_msg}
    
    def step3_convert_to_cnlp(self, subprompts_data: Dict[str, Any], code_generation_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        第三步：转换为CNLP格式
        调用 nl2cnlp.py 中的现有函数
        
        Args:
            subprompts_data: 子提示词数据
            code_generation_result: 代码生成结果，用于跳过已生成代码的子系统
        """
        LogUtils.log_step("第三步：转换为CNLP格式", "开始CNLP格式转换流程")
        self._notify_progress("转换CNLP", 0, "开始转换为CNLP格式...")
        
        try:
            # 添加数据类型验证和智能获取
            LogUtils.log_info(f"接收到的数据类型: {type(subprompts_data)}")
            LogUtils.log_info(f"数据内容预览: {str(subprompts_data)[:200]}")
            
            # 智能提取子提示词数据
            subprompts = self._extract_subprompts_from_data(subprompts_data)
            
            if not subprompts:
                LogUtils.log_error("没有子提示词可转换")
                return {"error": "没有子提示词可转换"}
            
            # 过滤掉已经成功生成代码的子系统
            filtered_subprompts, skipped_info = self._filter_subprompts_for_cnlp(subprompts, code_generation_result)
            
            if not filtered_subprompts:
                LogUtils.log_info("所有子系统都已生成代码，无需CNLP转换")
                return {
                    "cnlp_results": [],
                    "total_count": len(subprompts),
                    "success_count": 0,
                    "failed_count": 0,
                    "skipped_count": len(subprompts),
                    "skipped_info": skipped_info,
                    "original_subprompts": subprompts_data
                }
            
            LogUtils.log_info(f"开始转换 {len(filtered_subprompts)} 个子提示词...")
            LogUtils.log_info(f"跳过了 {len(subprompts) - len(filtered_subprompts)} 个已生成代码的子系统")
            
            # 使用现有的批量转换函数
            cnlp_results = batch_transform_cnlp(filtered_subprompts)
            
            # 过滤出成功转换的结果
            successful_results = []
            failed_count = 0
            
            for i, result in enumerate(cnlp_results):
                if result and result.strip():
                    successful_results.append({
                        "index": i,
                        "name": filtered_subprompts[i].get("name", f"子系统_{i+1}"),
                        "cnlp": result
                    })
                else:
                    failed_count += 1
                    LogUtils.log_warning(f"子提示词 {i+1} 转换失败")
            
            result = {
                "cnlp_results": successful_results,
                "total_count": len(subprompts),
                "success_count": len(successful_results),
                "failed_count": failed_count,
                "skipped_count": len(subprompts) - len(filtered_subprompts),
                "skipped_info": skipped_info,
                "original_subprompts": subprompts_data
            }
            
            LogUtils.log_success(f"第三步完成，成功转换 {len(successful_results)}/{len(subprompts)} 个子提示词")
            # 立即传递CNLP转换结果
            self._notify_progress("转换CNLP", 100, f"成功转换 {len(successful_results)}/{len(subprompts)} 个子提示词", result)
            return result
            
        except Exception as e:
            error_msg = f"CNLP转换失败: {e}"
            LogUtils.log_error(error_msg)
            return {"error": error_msg}
    
    def _filter_subprompts_for_cnlp(self, subprompts: List[Dict], code_generation_result: Dict[str, Any] = None) -> tuple:
        """
        过滤掉已经成功生成代码的子系统，避免重复转换为CNLP
        
        Args:
            subprompts: 原始子提示词列表
            code_generation_result: 代码生成结果
            
        Returns:
            tuple: (filtered_subprompts, skipped_info)
        """
        if not code_generation_result or "results" not in code_generation_result:
            LogUtils.log_info("没有代码生成结果，处理所有子系统")
            return subprompts, []
        
        code_results = code_generation_result["results"]
        filtered_subprompts = []
        skipped_info = []
        
        LogUtils.log_info("开始过滤已生成代码的子系统...")
        
        for i, subprompt in enumerate(subprompts):
            subprompt_name = subprompt.get("name", f"子系统_{i+1}")
            
            # 查找对应的代码生成结果
            code_result = None
            if i < len(code_results):
                code_result = code_results[i]
            
            # 检查是否已成功生成代码
            has_code = code_result and code_result.get("code") is not None
            
            if has_code:
                # 跳过已生成代码的子系统
                skipped_info.append({
                    "name": subprompt_name,
                    "reason": "已成功生成代码",
                    "code_length": len(code_result["code"]),
                    "test_cases_count": len(code_result.get("test_cases", []))
                })
                LogUtils.log_info(f"跳过子系统 '{subprompt_name}': 已生成代码 ({len(code_result['code'])} 字符)")
            else:
                # 保留需要CNLP转换的子系统
                filtered_subprompts.append(subprompt)
                if code_result:
                    is_implementable = code_result.get("is_implementable", False)
                    reason = code_result.get("reason", "未知")
                    if not is_implementable:
                        LogUtils.log_info(f"保留子系统 '{subprompt_name}': 不适合代码实现 ({reason})")
                    else:
                        LogUtils.log_info(f"保留子系统 '{subprompt_name}': 代码生成失败")
                else:
                    LogUtils.log_info(f"保留子系统 '{subprompt_name}': 无代码生成结果")
        
        LogUtils.log_info(f"过滤完成: 保留 {len(filtered_subprompts)} 个子系统，跳过 {len(skipped_info)} 个子系统")
        
        return filtered_subprompts, skipped_info
    
    def run_complete_pipeline(self, 
                             input_file: str = 'nl_prompt.txt',
                             save_intermediate: bool = True) -> Dict[str, Any]:
        """
        运行完整的拆分流程
        """
        LogUtils.log_step("完整流程", f"开始运行完整的提示词拆分流程，输入文件: {input_file}")
        
        # 读取原始提示词
        original_text = self.read_file(input_file)
        if not original_text:
            error_msg = f"无法读取输入文件 {input_file}"
            LogUtils.log_error(error_msg)
            return {"error": error_msg}
        
        LogUtils.log_info(f"原始文本长度: {len(original_text)} 字符")
        
        # 第一步：提取变量
        step1_result = self.step1_extract_variables(original_text)
        if "error" in step1_result:
            return step1_result
        
        if save_intermediate:
            self.save_json('output_step1_variables.json', step1_result)
            self.save_file('output_step1_text_with_vars.txt', step1_result['text_with_vars'])
        
        # 第二步：按照first_split.py的逻辑拆分
        step2_result = self.step2_split_to_subprompts(step1_result['text_with_vars'])
        if "error" in step2_result:
            return step2_result
        
        if save_intermediate:
            self.save_json('output_step2_split.json', step2_result)
            # 单独保存mermaid图
            if step2_result.get('mermaid_content'):
                self.save_file('output_step2_mermaid.txt', step2_result['mermaid_content'])
        
        # 第2.5步：生成代码（新增步骤）
        step2_5_result = self.step2_5_generate_code(step2_result.get('subprompts', {}))
        if "error" in step2_5_result:
            LogUtils.log_warning(f"代码生成失败，但继续执行后续步骤: {step2_5_result['error']}")
            step2_5_result = {"error": step2_5_result["error"], "results": []}
        
        if save_intermediate:
            self.save_json('output_step2_5_code.json', step2_5_result)
        
        # 第三步：转换为CNLP（跳过已生成代码的子系统）
        step3_result = self.step3_convert_to_cnlp(step2_result, step2_5_result)
        if "error" in step3_result:
            return step3_result
        
        if save_intermediate:
            self.save_json('output_step3_cnlp.json', step3_result)
        
        # 保存最终结果
        final_result = {
            "step1_variables": step1_result,
            "step2_split": step2_result,
            "step2_5_code": step2_5_result,
            "step3_cnlp": step3_result,
            "summary": {
                "input_file": input_file,
                "variables_count": len(step1_result.get('variables', [])),
                "subsystems_count": step2_result.get('statistics', {}).get('subsystems_count', 0),
                "subprompts_count": step2_result.get('statistics', {}).get('subprompts_count', 0),
                "code_implementable_count": step2_5_result.get('summary', {}).get('implementable_count', 0),
                "code_successful_count": step2_5_result.get('summary', {}).get('successful_count', 0),
                "code_failed_count": step2_5_result.get('summary', {}).get('failed_count', 0),
                "cnlp_success_count": step3_result.get('success_count', 0),
                "cnlp_failed_count": step3_result.get('failed_count', 0),
                "cnlp_skipped_count": step3_result.get('skipped_count', 0)
            }
        }
        
        if save_intermediate:
            self.save_json('output_final_result.json', final_result)
        
        # 使用日志系统输出完成信息
        LogUtils.log_success("完整流程执行完成！")
        LogUtils.log_info("统计结果:")
        LogUtils.log_info(f"   - 提取变量数量: {final_result['summary']['variables_count']}")
        LogUtils.log_info(f"   - 子系统数量: {final_result['summary']['subsystems_count']}")
        LogUtils.log_info(f"   - 子提示词数量: {final_result['summary']['subprompts_count']}")
        LogUtils.log_info(f"   - 可实现代码数量: {final_result['summary']['code_implementable_count']}")
        LogUtils.log_info(f"   - 成功生成代码数量: {final_result['summary']['code_successful_count']}")
        LogUtils.log_info(f"   - 代码生成失败数量: {final_result['summary']['code_failed_count']}")
        LogUtils.log_info(f"   - CNLP转换成功: {final_result['summary']['cnlp_success_count']}")
        LogUtils.log_info(f"   - CNLP转换失败: {final_result['summary']['cnlp_failed_count']}")
        LogUtils.log_info(f"   - CNLP转换跳过: {final_result['summary']['cnlp_skipped_count']} (已生成代码)")
        LogUtils.log_info("输出文件:")
        LogUtils.log_info("   - output_step1_variables.json: 变量提取结果")
        LogUtils.log_info("   - output_step1_text_with_vars.txt: 标记变量的文本")
        LogUtils.log_info("   - output_step2_split.json: 完整拆分结果")
        LogUtils.log_info("   - output_step2_mermaid.txt: Mermaid流程图")
        LogUtils.log_info("   - output_step2_5_code.json: 代码生成结果")
        LogUtils.log_info("   - gen_code/output/: 生成的代码文件")
        LogUtils.log_info("   - output_step3_cnlp.json: CNLP转换结果")
        LogUtils.log_info("   - output_final_result.json: 完整结果")
        
        return final_result


def main():
    """主函数 - 简洁的流程控制（重构后版本）"""
    LogUtils.log_step("提示词拆分系统", "流程编排器启动")
    
    try:
        # 创建流程编排器实例
        pipeline = PromptSplitPipeline()
        
        # 运行完整流程
        result = pipeline.run_complete_pipeline(
            input_file='nl_prompt.txt',
            save_intermediate=True
        )
        
        if "error" in result:
            LogUtils.log_error(f"执行失败: {result['error']}")
            return False
        else:
            LogUtils.log_success("所有步骤执行成功！")
            return True
            
    except Exception as e:
        LogUtils.log_error(f"主函数执行异常: {e}")
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1) 