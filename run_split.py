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
        LogUtils.log_info("     🔍 查找第一个 '{' 字符...")
        start_idx = response.find('{')
        if start_idx == -1:
            LogUtils.log_info("     ❌ 未找到 '{' 字符")
            return {}
        
        LogUtils.log_info(f"     ✅ 找到起始位置: {start_idx}")
        LogUtils.log_info(f"     📖 起始位置周围文本: ...{response[max(0, start_idx-20):start_idx+50]}...")
        
        brace_count = 0
        end_idx = -1
        for i, char in enumerate(response[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if end_idx == -1:
            LogUtils.log_info(f"     ❌ 未找到匹配的 '}}' 字符，最终括号计数: {brace_count}")
            return {}
        
        json_str = response[start_idx:end_idx+1]
        LogUtils.log_info(f"     ✅ 找到完整JSON块，长度: {len(json_str)} 字符")
        LogUtils.log_info(f"     📖 JSON开头: {json_str[:100]}...")
        LogUtils.log_info(f"     📖 JSON结尾: ...{json_str[-100:]}")
        
        try:
            result = json.loads(json_str)
            LogUtils.log_info(f"     ✅ JSON解析成功，类型: {type(result)}")
            return result
        except json.JSONDecodeError as e:
            LogUtils.log_info(f"     ❌ JSON解析失败: {e}")
            raise

    def _extract_json_strategy_2(self, response: str) -> Dict[str, Any]:
        """策略2: 提取```json代码块中的JSON"""
        import re
        
        LogUtils.log_info("     🔍 查找 ```json 代码块...")
        
        # 查找 ```json 代码块
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_block_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if match:
            json_str = match.group(1)
            LogUtils.log_info(f"     ✅ 找到代码块，JSON长度: {len(json_str)} 字符")
            LogUtils.log_info(f"     📍 代码块位置: {match.start()}-{match.end()}")
            LogUtils.log_info(f"     📖 JSON内容开头: {json_str[:100]}...")
            
            try:
                result = json.loads(json_str)
                LogUtils.log_info(f"     ✅ JSON解析成功")
                return result
            except json.JSONDecodeError as e:
                LogUtils.log_info(f"     ❌ JSON解析失败: {e}")
                raise
        else:
            LogUtils.log_info("     ❌ 未找到 ```json 代码块")
            # 尝试查找没有json标识的代码块
            generic_pattern = r'```\s*(\{.*?\})\s*```'
            generic_match = re.search(generic_pattern, response, re.DOTALL)
            if generic_match:
                LogUtils.log_info("     🔄 尝试通用代码块模式...")
                json_str = generic_match.group(1)
                LogUtils.log_info(f"     ✅ 找到通用代码块，JSON长度: {len(json_str)} 字符")
                try:
                    result = json.loads(json_str)
                    LogUtils.log_info(f"     ✅ 通用代码块JSON解析成功")
                    return result
                except json.JSONDecodeError as e:
                    LogUtils.log_info(f"     ❌ 通用代码块JSON解析失败: {e}")
                    raise
            else:
                LogUtils.log_info("     ❌ 也未找到通用代码块")
        
        return {}

    def _extract_json_strategy_3(self, response: str) -> Dict[str, Any]:
        """策略3: 逐行搜索，查找以{开头的行"""
        LogUtils.log_info("     🔍 逐行搜索JSON结构...")
        
        lines = response.split('\n')
        json_lines = []
        in_json = False
        brace_count = 0
        start_line_num = -1
        
        LogUtils.log_info(f"     📊 总行数: {len(lines)}")
        
        for line_num, line in enumerate(lines):
            stripped = line.strip()
            if not in_json and stripped.startswith('{'):
                LogUtils.log_info(f"     ✅ 在第 {line_num+1} 行找到JSON起始: {stripped[:50]}...")
                in_json = True
                json_lines = [line]
                brace_count = line.count('{') - line.count('}')
                start_line_num = line_num + 1
                LogUtils.log_info(f"     📊 初始括号计数: {brace_count}")
            elif in_json:
                json_lines.append(line)
                line_braces = line.count('{') - line.count('}')
                brace_count += line_braces
                LogUtils.log_info(f"     📊 第 {line_num+1} 行，括号变化: {line_braces}，总计数: {brace_count}")
                if brace_count <= 0:
                    LogUtils.log_info(f"     ✅ 在第 {line_num+1} 行找到JSON结束")
                    break
        
        if json_lines:
            json_str = '\n'.join(json_lines)
            LogUtils.log_info(f"     ✅ 提取到JSON块，从第 {start_line_num} 行开始，共 {len(json_lines)} 行")
            LogUtils.log_info(f"     📖 JSON开头: {json_str[:100]}...")
            LogUtils.log_info(f"     📖 JSON结尾: ...{json_str[-100:]}")
            
            try:
                result = json.loads(json_str)
                LogUtils.log_info(f"     ✅ JSON解析成功")
                return result
            except json.JSONDecodeError as e:
                LogUtils.log_info(f"     ❌ JSON解析失败: {e}")
                raise
        else:
            LogUtils.log_info("     ❌ 未找到以 '{' 开头的行")
        
        return {}

    def _extract_json_strategy_4(self, response: str) -> Dict[str, Any]:
        """策略4: 使用公共工具的JSON提取"""
        from common_utils import JSONProcessor
        
        LogUtils.log_info("     🔍 使用公共工具JSONProcessor...")
        
        json_str = JSONProcessor.extract_json_string(response)
        LogUtils.log_info(f"     📊 提取结果长度: {len(json_str)} 字符")
        LogUtils.log_info(f"     📊 原始响应长度: {len(response)} 字符")
        
        if json_str and json_str != response:  # 确保提取到了JSON
            LogUtils.log_info("     ✅ 成功提取到JSON字符串")
            LogUtils.log_info(f"     📖 提取的JSON开头: {json_str[:100]}...")
            LogUtils.log_info(f"     📖 提取的JSON结尾: ...{json_str[-100:]}")
            
            try:
                result = json.loads(json_str)
                LogUtils.log_info(f"     ✅ JSON解析成功")
                return result
            except json.JSONDecodeError as e:
                LogUtils.log_info(f"     ❌ JSON解析失败: {e}")
                raise
        else:
            if not json_str:
                LogUtils.log_info("     ❌ JSONProcessor返回空结果")
            elif json_str == response:
                LogUtils.log_info("     ❌ JSONProcessor返回原始响应，未找到JSON")
            else:
                LogUtils.log_info("     ❌ JSONProcessor提取异常")
        
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
        
        LogUtils.log_info("🔍 开始提取子提示词JSON数据...")
        LogUtils.log_info(f"   原始响应长度: {len(response)} 字符")
        
        # 复用子系统的提取策略，但检查不同的字段
        strategies = [
            ("策略1: 完整JSON块匹配", self._extract_json_strategy_1),
            ("策略2: 代码块JSON提取", self._extract_json_strategy_2),
            ("策略3: 逐行JSON搜索", self._extract_json_strategy_3),
            ("策略4: 公共工具提取", self._extract_json_strategy_4),
            ("策略5: JSON修复并重试", self._extract_json_strategy_5_fix_and_retry)
        ]
        
        for i, (strategy_name, strategy_func) in enumerate(strategies, 1):
            LogUtils.log_info(f"🔧 尝试 {strategy_name}...")
            try:
                result = strategy_func(response)
                
                LogUtils.log_info(f"   策略 {i} 执行结果:")
                LogUtils.log_info(f"     - 返回类型: {type(result)}")
                
                if result:
                    LogUtils.log_info(f"     - 返回内容长度: {len(str(result))} 字符")
                    LogUtils.log_info(f"     - 顶级键: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                    
                    # 检查是否包含子提示词相关字段
                    target_fields = ["subprompts", "sub_prompts", "prompts", "subPrompts"]
                    found_fields = []
                    for field in target_fields:
                        if field in result:
                            field_value = result[field]
                            found_fields.append(f"{field}({type(field_value).__name__}, {len(field_value) if hasattr(field_value, '__len__') else 'N/A'})")
                    
                    if found_fields:
                        LogUtils.log_success(f"✅ 策略 {i} 成功！找到字段: {', '.join(found_fields)}")
                        
                        # 统一字段名
                        if "sub_prompts" in result and "subprompts" not in result:
                            result["subprompts"] = result.pop("sub_prompts")
                            LogUtils.log_info("     - 已将 'sub_prompts' 重命名为 'subprompts'")
                        
                        return result
                    else:
                        LogUtils.log_warning(f"⚠️ 策略 {i} 提取到JSON但无子提示词字段")
                        LogUtils.log_info(f"     - 找到的字段: {list(result.keys())}")
                        
                        # 显示JSON内容的片段（如果不太长）
                        if len(str(result)) < 1000:
                            LogUtils.log_info(f"     - JSON内容预览: {result}")
                        else:
                            LogUtils.log_info(f"     - JSON内容过长，仅显示前500字符: {str(result)[:500]}...")
                else:
                    LogUtils.log_info("     - 返回空结果")
                    
            except json.JSONDecodeError as e:
                LogUtils.log_warning(f"❌ 策略 {i} JSON解析失败: {e}")
                LogUtils.log_info(f"     - 错误位置: 行 {getattr(e, 'lineno', '未知')}，列 {getattr(e, 'colno', '未知')}")
                LogUtils.log_info(f"     - 错误字符位置: {getattr(e, 'pos', '未知')}")
                
                # 尝试显示错误位置周围的内容
                if hasattr(e, 'pos') and e.pos is not None:
                    start = max(0, e.pos - 100)
                    end = min(len(response), e.pos + 100)
                    error_context = response[start:end]
                    LogUtils.log_info(f"     - 错误位置周围内容: ...{error_context}...")
                    
            except Exception as e:
                LogUtils.log_warning(f"❌ 策略 {i} 执行失败: {type(e).__name__}: {e}")
                import traceback
                LogUtils.log_info(f"     - 详细错误: {traceback.format_exc()}")
        
        LogUtils.log_error("❌ 所有子提示词JSON提取策略均失败")
        LogUtils.log_info("🔍 提供额外调试信息:")
        
        # 提供一些调试提示
        if '{' not in response:
            LogUtils.log_info("   - 响应中没有找到 '{' 字符，可能不包含JSON")
        elif '}' not in response:
            LogUtils.log_info("   - 响应中没有找到 '}' 字符，JSON可能不完整")
        else:
            first_brace = response.find('{')
            last_brace = response.rfind('}')
            LogUtils.log_info(f"   - 第一个 '{{' 位置: {first_brace}")
            LogUtils.log_info(f"   - 最后一个 '}}' 位置: {last_brace}")
            
            if first_brace != -1 and last_brace != -1:
                potential_json = response[first_brace:last_brace+1]
                LogUtils.log_info(f"   - 潜在JSON长度: {len(potential_json)} 字符")
                LogUtils.log_info(f"   - 潜在JSON开头: {potential_json[:200]}...")
                
        return {}

    def _extract_json_strategy_5_fix_and_retry(self, response: str) -> Dict[str, Any]:
        """策略5: JSON修复并重试"""
        LogUtils.log_info("     🔧 尝试修复JSON格式问题...")
        
        # 先尝试找到JSON部分
        start_idx = response.find('{')
        if start_idx == -1:
            LogUtils.log_info("     ❌ 未找到JSON起始标记")
            return {}
        
        # 找到匹配的结束位置
        brace_count = 0
        end_idx = -1
        for i, char in enumerate(response[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if end_idx == -1:
            LogUtils.log_info("     ❌ 未找到JSON结束标记")
            return {}
        
        json_str = response[start_idx:end_idx+1]
        LogUtils.log_info(f"     📖 提取到原始JSON，长度: {len(json_str)} 字符")
        
        # 应用多种修复策略
        fixed_json = self._apply_json_fixes(json_str)
        
        if fixed_json != json_str:
            LogUtils.log_info(f"     🔧 JSON已修复，修复后长度: {len(fixed_json)} 字符")
            LogUtils.log_info(f"     📖 修复后JSON开头: {fixed_json[:200]}...")
        else:
            LogUtils.log_info("     ℹ️ JSON无需修复")
        
        try:
            result = json.loads(fixed_json)
            LogUtils.log_info(f"     ✅ 修复后JSON解析成功")
            return result
        except json.JSONDecodeError as e:
            LogUtils.log_info(f"     ❌ 修复后仍然解析失败: {e}")
            raise

    def _apply_json_fixes(self, json_str: str) -> str:
        """应用多种JSON修复策略"""
        LogUtils.log_info("     🛠️ 应用JSON修复策略...")
        
        fixed = json_str
        fixes_applied = []
        
        import re
        
        # 修复1: 最强力的字符串字段修复
        # 使用更强的策略来处理所有字符串值中的引号问题
        def fix_all_string_fields(text):
            """修复所有JSON字符串字段中的未转义引号"""
            # 查找所有的字符串值（在冒号后面的引号内容）
            pattern = r'("(?:prompt|name|inputs|outputs|collaboration|[^"]+)":\s*")([^"}]*(?:[^"\\]"[^"}]*)*)"'
            
            def fix_field_value(match):
                field_start = match.group(1)  # "field": "
                content = match.group(2)      # 字段内容（可能包含未转义引号）
                
                LogUtils.log_info(f"     🔧 修复字段内容，原长度: {len(content)}")
                
                # 保护已经转义的引号
                content = content.replace('\\"', '###ALREADY_ESCAPED###')
                
                # 转义所有未转义的引号
                content = content.replace('"', '\\"')
                
                # 恢复之前已转义的引号
                content = content.replace('###ALREADY_ESCAPED###', '\\"')
                
                LogUtils.log_info(f"     ✅ 字段修复完成，新长度: {len(content)}")
                
                return field_start + content + '"'
            
            # 使用多次匹配来确保所有字段都被处理
            attempts = 0
            while attempts < 5:  # 最多尝试5次
                new_text = re.sub(pattern, fix_field_value, text, flags=re.DOTALL)
                if new_text == text:
                    break  # 没有更多修复可做
                text = new_text
                attempts += 1
                LogUtils.log_info(f"     🔄 修复轮次 {attempts}")
            
            return text
        
        original_fixed = fixed
        fixed = fix_all_string_fields(fixed)
        if fixed != original_fixed:
            fixes_applied.append("强力字段修复")
        
        # 修复2: 特殊中文标点修复
        chinese_patterns = [
            ('"，"', '\\"，\\"'),    # 中文逗号
            ('"。"', '\\"。\\"'),    # 中文句号
            ('"："', '\\"：\\"'),    # 中文冒号
            ('"（"', '\\"（\\"'),    # 中文左括号
            ('"）"', '\\"）\\"'),    # 中文右括号
        ]
        
        for pattern, replacement in chinese_patterns:
            if pattern in fixed:
                fixed = fixed.replace(pattern, replacement)
                fixes_applied.append(f"修复中文标点{pattern[1]}")
                LogUtils.log_info(f"     🔧 修复中文标点: {pattern}")
        
        # 修复3: 清理控制字符
        import unicodedata
        cleaned = ''.join(
            char for char in fixed 
            if unicodedata.category(char)[0] != 'C' 
            or char in ['\n', '\r', '\t', ' ']
        )
        if len(cleaned) != len(fixed):
            fixed = cleaned
            fixes_applied.append("清理控制字符")
        
        # 修复4: 移除多余的逗号
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        
        # 修复5: 最后的检查和平衡引号
        # 确保所有的字符串都正确闭合
        try:
            # 尝试快速验证是否还有明显的语法错误
            brace_count = fixed.count('{') - fixed.count('}')
            bracket_count = fixed.count('[') - fixed.count(']')
            
            if brace_count != 0:
                LogUtils.log_info(f"     ⚠️ 大括号不平衡: {brace_count}")
            if bracket_count != 0:
                LogUtils.log_info(f"     ⚠️ 方括号不平衡: {bracket_count}")
                
        except Exception as e:
            LogUtils.log_info(f"     ⚠️ 语法检查异常: {e}")
        
        if fixes_applied:
            LogUtils.log_info(f"     ✅ 应用的修复策略: {', '.join(fixes_applied)}")
        else:
            LogUtils.log_info("     ℹ️ 未发现需要修复的问题")
        
        return fixed

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
            
            LogUtils.log_info("🔍 准备生成子提示词的输入内容:")
            LogUtils.log_info(f"   - 原始文本长度: {len(original_text)} 字符")
            LogUtils.log_info(f"   - 子系统数量: {len(subsystems_data.get('subsystems', []))}")
            LogUtils.log_info(f"   - 用户内容长度: {len(user_content)} 字符")
            LogUtils.log_info(f"   - 用户内容预览: {user_content[:200]}...")
            
            # 创建包含子系统信息的消息列表
            messages = sub_prompt_messages.copy()
            messages.append({"role": "user", "content": user_content})
            
            LogUtils.log_info("🚀 调用LLM生成子提示词...")
            
            # 调用LLM生成子提示词
            response = llm_client.call(messages)
            
            LogUtils.log_info("📝 LLM响应详细信息:")
            if response:
                LogUtils.log_info(f"   - 响应长度: {len(response)} 字符")
                LogUtils.log_info(f"   - 响应类型: {type(response)}")
                LogUtils.log_info("   - 响应前500字符:")
                LogUtils.log_info(f"     {response[:500]}")
                LogUtils.log_info("   - 响应后500字符:")
                LogUtils.log_info(f"     ...{response[-500:]}")
                
                # 分析响应中可能的JSON结构
                json_start_count = response.count('{')
                json_end_count = response.count('}')
                array_start_count = response.count('[')
                array_end_count = response.count(']')
                
                LogUtils.log_info("   - JSON结构分析:")
                LogUtils.log_info(f"     大括号开始: {json_start_count}, 结束: {json_end_count}")
                LogUtils.log_info(f"     方括号开始: {array_start_count}, 结束: {array_end_count}")
                
                # 查找关键词
                key_words = ["subprompts", "sub_prompts", "prompts", "subPrompts"]
                for word in key_words:
                    count = response.count(word)
                    if count > 0:
                        LogUtils.log_info(f"     找到关键词 '{word}': {count} 次")
                        # 显示关键词周围的文本
                        import re
                        matches = list(re.finditer(re.escape(word), response, re.IGNORECASE))
                        for i, match in enumerate(matches[:3]):  # 最多显示3个匹配
                            start = max(0, match.start() - 50)
                            end = min(len(response), match.end() + 50)
                            context = response[start:end].replace('\n', ' ')
                            LogUtils.log_info(f"       匹配{i+1}: ...{context}...")
            else:
                LogUtils.log_error("❌ LLM返回空响应")
                return {"subprompts": []}
            
            # 改进的JSON提取逻辑（复用子系统的提取方法）
            LogUtils.log_info("🔧 开始JSON提取过程...")
            subprompts_data = self._extract_subprompts_json(response)
            if subprompts_data and "subprompts" in subprompts_data:
                LogUtils.log_success(f"✅ 成功提取子提示词数据，包含 {len(subprompts_data['subprompts'])} 个子提示词")
                return subprompts_data
            else:
                LogUtils.log_warning("⚠️ 未找到有效的子提示词JSON数据")
                LogUtils.log_info("💾 完整响应内容（调试用）:")
                LogUtils.log_info("=" * 60)
                LogUtils.log_info(response)
                LogUtils.log_info("=" * 60)
                return {"subprompts": []}
                
        except Exception as e:
            LogUtils.log_error(f"❌ 子提示词生成失败: {e}")
            import traceback
            LogUtils.log_error(f"   错误详情: {traceback.format_exc()}")
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
    
    def step2_5_generate_code(self, step2_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        第2.5步：为子系统生成代码和流程图（在第二步和第三步之间插入）
        """
        # 获取代码生成配置
        code_config = self.config.get('step2_5_code_generation', {})
        
        # 检查是否启用代码生成
        if not code_config.get('enabled', True):
            LogUtils.log_info("代码生成功能已禁用，跳过此步骤")
            return {
                "summary": {"total_count": 0, "implementable_count": 0, "successful_count": 0, "failed_count": 0},
                "results": [],
                "disabled": True
            }
        
        LogUtils.log_step("第2.5步：生成代码", "开始为子系统生成代码实现和流程图")
        self._notify_progress("代码生成", 0, "开始为子系统生成代码和流程图...")
        
        try:
            parallel_enabled = code_config.get('parallel_processing', True)
            max_workers = code_config.get('max_workers', 3)
            mermaid_enabled = code_config.get('generate_mermaid', True)
            
            LogUtils.log_info(f"代码生成配置: 并行处理={parallel_enabled}, 最大线程数={max_workers}, 生成流程图={mermaid_enabled}")
            
            # 从step2结果中提取数据
            subsystems_data = step2_result.get("subsystems", {})
            subprompts_data = step2_result.get("subprompts", {})
            
            # 初始化结果
            code_results = {
                "summary": {"total_count": 0, "implementable_count": 0, "successful_count": 0, "failed_count": 0},
                "results": []
            }
            
            # 1. 代码生成部分（使用简化的方法）
            if subsystems_data and subsystems_data.get("subsystems"):
                LogUtils.log_info("发现子系统数据，但简化版本暂不支持子系统代码生成")
                LogUtils.log_info("将所有子系统标记为CNLP实现")
                
                # 标记所有子系统为CNLP实现
                subsystems = subsystems_data["subsystems"]
                for subsystem in subsystems:
                    subsystem["actual_implementation"] = "CNLP"
                    if "cnlp" not in subsystem:
                        subsystem["cnlp"] = f"需要通过自然语言处理实现：{subsystem.get('description', subsystem.get('name', ''))}"
                
                code_results["summary"]["total_count"] = len(subsystems)
                
                # 确保subsystems_data包含collaboration字段
                if "collaboration" not in subsystems_data or not subsystems_data["collaboration"]:
                    # 生成默认的协作关系描述
                    subsystem_names = [s.get("name", f"子系统{i+1}") for i, s in enumerate(subsystems)]
                    if len(subsystem_names) <= 1:
                        default_collaboration = f"单个子系统 {subsystem_names[0] if subsystem_names else '未命名子系统'} 独立处理用户请求"
                    else:
                        default_collaboration = f"系统按顺序执行：{' → '.join(subsystem_names)}，每个子系统处理特定的业务逻辑"
                    
                    subsystems_data["collaboration"] = default_collaboration
                    LogUtils.log_info(f"生成默认协作关系: {default_collaboration}")
                
            elif subprompts_data and subprompts_data.get("subprompts"):
                LogUtils.log_info("使用子提示词数据进行代码生成")
                # 使用简化的子提示词处理方法
                code_results = self.code_generator.batch_process_subprompts(
                    subprompts_data, 
                    parallel=parallel_enabled, 
                    max_workers=max_workers
                )
            else:
                LogUtils.log_warning("没有找到可处理的子系统或子提示词数据")
            
            # 2. 独立生成mermaid流程图（无论是否有代码生成）
            mermaid_code = None
            if mermaid_enabled:
                try:
                    from mermaid_generator import MermaidGenerator
                    mermaid_generator = MermaidGenerator()
                    
                    # 确定使用哪种数据生成流程图
                    if subsystems_data and subsystems_data.get("subsystems"):
                        LogUtils.log_info("基于子系统数据生成系统流程图...")
                        mermaid_code = mermaid_generator.generate_mermaid_diagram(subsystems_data, quiet=False)
                    elif subprompts_data and subprompts_data.get("subprompts"):
                        LogUtils.log_info("基于子提示词数据生成系统流程图...")
                        # 将子提示词数据转换为subsystems格式
                        converted_data = self._convert_subprompts_to_subsystems_format(subprompts_data, code_results)
                        mermaid_code = mermaid_generator.generate_mermaid_diagram(converted_data, quiet=False)
                    
                    if mermaid_code:
                        LogUtils.log_success("系统流程图生成完成")
                        code_results["mermaid_diagram"] = mermaid_code
                    else:
                        LogUtils.log_warning("系统流程图生成失败")
                        
                except Exception as e:
                    LogUtils.log_error(f"系统流程图生成异常: {e}")
            
            # 3. 统计和报告
            summary = code_results.get("summary", {})
            total_count = summary.get("total_count", summary.get("total_subprompts", 0))
            implementable_count = summary.get("implementable_count", 0)
            successful_count = summary.get("successful_count", 0)
            
            LogUtils.log_success(f"代码生成和流程图生成完成")
            LogUtils.log_info(f"   - 总数量: {total_count}")
            LogUtils.log_info(f"   - 可实现数: {implementable_count}")
            LogUtils.log_info(f"   - 成功生成代码数: {successful_count}")
            LogUtils.log_info(f"   - 流程图生成: {'✅成功' if mermaid_code else '❌失败'}")
            
            # 4. 保存结果
            try:
                self.code_generator.save_code_generation_results(code_results)
                LogUtils.log_success("代码生成结果已保存")
            except Exception as e:
                LogUtils.log_warning(f"保存代码生成结果失败: {e}")
            
            # 5. 通知进度完成
            self._notify_progress("代码生成", 100, f"完成代码生成和流程图生成", code_results)
            
            return code_results
            
        except Exception as e:
            error_msg = f"代码生成流程失败: {e}"
            LogUtils.log_error(error_msg)
            return {"error": error_msg}
    
    def _convert_subprompts_to_subsystems_format(self, subprompts_data: Dict[str, Any], code_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        将子提示词数据转换为subsystems格式，用于mermaid流程图生成
        
        Args:
            subprompts_data: 子提示词数据
            code_results: 代码生成结果
            
        Returns:
            转换后的subsystems格式数据
        """
        try:
            subprompts = subprompts_data.get("subprompts", [])
            collaboration = subprompts_data.get("collaboration", "")
            
            # 从代码生成结果中获取实现状态
            implementation_map = {}
            for result in code_results.get("results", []):
                name = result.get("name", "")
                has_code = bool(result.get("code"))
                implementation_map[name] = "CODE" if has_code else "CNLP"
            
            # 转换为subsystems格式
            subsystems = []
            for subprompt in subprompts:
                name = subprompt.get("name", "")
                implementation = implementation_map.get(name, "CNLP")
                
                subsystem = {
                    "name": name,
                    "description": subprompt.get("prompt", "")[:100] + "...",
                    "actual_implementation": implementation
                }
                
                if implementation == "CODE":
                    # 从代码生成结果中找到对应的代码
                    for result in code_results.get("results", []):
                        if result.get("name") == name and result.get("code"):
                            subsystem["code"] = result["code"]
                            break
                else:
                    subsystem["cnlp"] = f"需要通过自然语言处理实现：{name}"
                
                subsystems.append(subsystem)
            
            # 如果collaboration为空，生成默认的协作关系描述
            if not collaboration:
                subsystem_names = [s.get("name", f"子系统{i+1}") for i, s in enumerate(subsystems)]
                if len(subsystem_names) <= 1:
                    collaboration = f"单个子系统 {subsystem_names[0] if subsystem_names else '未命名子系统'} 独立处理用户请求"
                else:
                    collaboration = f"系统按顺序执行：{' → '.join(subsystem_names)}，每个子系统处理特定的业务逻辑"
                
                LogUtils.log_info(f"为子提示词数据生成默认协作关系: {collaboration}")
            
            return {
                "subsystems": subsystems,
                "collaboration": collaboration
            }
            
        except Exception as e:
            LogUtils.log_warning(f"转换子提示词格式失败: {e}")
            return {"subsystems": [], "collaboration": ""}
    
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
        
        # 第2.5步：生成代码（新增步骤，可配置禁用）
        code_generation_enabled = self.config.get('step2_5_code_generation', {}).get('enabled', True)
        
        if code_generation_enabled:
            step2_5_result = self.step2_5_generate_code(step2_result)
            if "error" in step2_5_result:
                LogUtils.log_warning(f"代码生成失败，但继续执行后续步骤: {step2_5_result['error']}")
                step2_5_result = {"error": step2_5_result["error"], "results": []}
            
            if save_intermediate:
                self.save_json('output_step2_5_code.json', step2_5_result)
        else:
            LogUtils.log_info("代码生成步骤已禁用，跳过...")
            step2_5_result = {
                "summary": {"total_count": 0, "implementable_count": 0, "successful_count": 0, "failed_count": 0},
                "results": [],
                "disabled": True
            }
        
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