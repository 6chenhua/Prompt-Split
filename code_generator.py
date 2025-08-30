"""
代码生成模块
整合gen_code目录中的功能，为子系统生成代码实现
"""

import json
import re
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from LLMTool import LLMApiClient
from common_utils import LogUtils, FileUtils, JSONProcessor

class CodeGenerator:
    """代码生成器类"""
    
    def __init__(self):
        self.llm_client = LLMApiClient()
        LogUtils.log_info("代码生成器初始化完成")
    
    def _load_prompt_template(self, template_name: str) -> str:
        """
        加载提示词模板
        
        Args:
            template_name: 模板名称 (code, judge, case)
            
        Returns:
            提示词模板内容
        """
        template_map = {
            "code": """prompt CODE{
@Persona {
您是一名资深 Python 工程师，具备代码修复与优化能力。
}
@Description {
您的角色是：根据自然语言需求与实现注释生成代码，如果提供了错误信息，您需要对代码进行修复。
}
@ContextControl {
@Rules {
1. 必须输出 Python 代码，包裹在 markdown 代码块 ```python ``` 内。
2. 如果输入包含错误信息，请只针对该错误进行修复，不要完全重写无关部分。
3. 输出的代码必须完整、可运行。只输出函数定义，不要添加任何示例调用、变量赋值或 print 语句
4. 不要输出解释性文字，只能输出代码。也不需要生成测试代码之类的解释，只要完成需要的功能就行
}
}
@Instruction Split prompt and order {
@InputVariable {
- 用户的自然语言需求
- 可能包含的实现注释
- 如果有：运行错误信息（仅保留关键错误原因）
}
@Commands {
step1: 阅读需求和注释。
step2: 如果没有错误信息，生成完整代码。
step3: 如果有错误信息，只修复导致错误的部分。
step4: 输出完整 Python 代码，必须用 ```python ``` 包裹。
}
@OutputVariable {
```python
# Python 代码
}
}
@Format {
输出严格遵循 Python 代码块格式。
}
}""",
            
            "judge": """prompt JUDGE{
@Persona {
您是一个经验丰富的软件架构师和AI推理专家。
}
@Description {
您的角色是：分析输入的自然语言需求，判断其是否能通过Python代码实现。
}
@ContextControl {
@Rules {
1. 如果可以实现，您需要输出一个 JSON。
2. JSON 必须包含字段：
   - "is_implementable": 布尔值 (true/false)
   - "annotation": 如果可实现，提供实现思路（简明步骤）
   - "reason": 如果不可实现，说明理由。
3. 输出必须是合法 JSON，不能包含多余文字或解释。
}
}
@Instruction Split prompt and order {
@InputVariable {
输入的 prompt (自然语言需求)。
}
@Commands {
step1: 阅读输入需求。
step2: 判断是否可以用代码实现。
step3: 如果能实现，写出 "annotation" 简要说明实现方式。
step4: 如果不能实现，写出 "reason"。
step5: 返回 JSON 格式结果。
}
@OutputVariable {
{
  "is_implementable": true/false,
  "annotation": "如果能实现的注释",
  "reason": "如果不能实现的理由"
}
}
}
@Format {
输出严格遵循 JSON 格式，不要有其他文字。
}
}""",
            
            "case": """prompt CASE{
@Persona {
您是一名资深 Python 测试工程师，具备生成多样化测试用例的能力，能够覆盖边缘案例、正常案例和异常案例。
}
@Description {
您的角色是：根据自然语言需求、已生成的代码（如果提供）和指定生成数量，生成测试用例列表。测试用例必须包括输入代码（用于执行的 Python 语句）和预期输出（字符串形式）。
}
@ContextControl {
@Rules {

输出必须是 JSON 格式，结构为 {"test_cases": [{"input_code": "Python 执行语句", "expected_output": "预期输出字符串"}, ...]}。
生成的测试用例数量必须严格等于指定的生成数量，如果未指定，默认生成 10 个。
如果提供了已生成的代码，请基于该代码的实现生成更精确的测试用例；否则，仅基于需求生成。
测试用例应多样化，包括正常输入、边界值、错误输入等。
包裹在 markdown 代码块 ```json
不要输出解释性文字，只能输出 JSON。
}
}
@Instruction Split prompt and order {
@InputVariable {


用户的自然语言需求
如果有：已生成的 Python 代码
生成数量（整数，默认 10）
}
@Commands {
step1: 阅读需求和生成数量。
step2: 如果提供了代码，分析代码逻辑以生成针对性的测试用例；否则，基于需求推断函数签名和行为。
step3: 生成指定数量的多样化测试用例，确保每个用例有 input_code（可执行语句，如 "print(function_name(args))"）和 expected_output（字符串）。
step4: 输出 JSON 格式的测试用例列表，用 json  包裹。
}
@OutputVariable {

json{"test_cases": [{"input_code": "...", "expected_output": "..."}, ...]}
}
@Format {
输出严格遵循 JSON 代码块格式。
}
}"""
        }
        
        return template_map.get(template_name, "")
    
    def judge_implementability(self, requirement: str) -> Dict[str, Any]:
        """
        判断需求是否可以通过代码实现
        
        Args:
            requirement: 自然语言需求描述
            
        Returns:
            判断结果字典
        """
        LogUtils.log_info("开始判断需求可实现性...")
        
        try:
            judge_prompt = self._load_prompt_template("judge")
            
            messages = [
                {"role": "system", "content": judge_prompt},
                {"role": "user", "content": requirement}
            ]
            
            response = self.llm_client.call(messages)
            if not response:
                return {"is_implementable": False, "reason": "LLM调用失败"}
            
            # 提取JSON结果
            try:
                result = json.loads(response)
                LogUtils.log_success(f"可实现性判断完成: {result['is_implementable']}")
                return result
            except json.JSONDecodeError:
                # 尝试从响应中提取JSON
                json_str = JSONProcessor.extract_json_string(response)
                if json_str:
                    result = json.loads(json_str)
                    LogUtils.log_success(f"可实现性判断完成: {result['is_implementable']}")
                    return result
                else:
                    LogUtils.log_warning("无法解析判断结果")
                    return {"is_implementable": False, "reason": "响应格式错误"}
                    
        except Exception as e:
            LogUtils.log_error(f"判断可实现性失败: {e}")
            return {"is_implementable": False, "reason": f"处理异常: {e}"}
    
    def judge_implementability_quiet(self, requirement: str, quiet: bool = False) -> Dict[str, Any]:
        """
        判断需求是否可以通过代码实现（支持安静模式）
        """
        if not quiet:
            LogUtils.log_info("开始判断需求可实现性...")
        
        try:
            judge_prompt = self._load_prompt_template("judge")
            
            messages = [
                {"role": "system", "content": judge_prompt},
                {"role": "user", "content": requirement}
            ]
            
            response = self.llm_client.call(messages)
            if not response:
                return {"is_implementable": False, "reason": "LLM调用失败"}
            
            # 提取JSON结果
            try:
                result = json.loads(response)
                if not quiet:
                    LogUtils.log_success(f"可实现性判断完成: {result['is_implementable']}")
                return result
            except json.JSONDecodeError:
                # 尝试从响应中提取JSON
                json_str = JSONProcessor.extract_json_string(response)
                if json_str:
                    result = json.loads(json_str)
                    if not quiet:
                        LogUtils.log_success(f"可实现性判断完成: {result['is_implementable']}")
                    return result
                else:
                    if not quiet:
                        LogUtils.log_warning("无法解析判断结果")
                    return {"is_implementable": False, "reason": "响应格式错误"}
                    
        except Exception as e:
            if not quiet:
                LogUtils.log_error(f"判断可实现性失败: {e}")
            return {"is_implementable": False, "reason": f"处理异常: {e}"}
    
    def generate_code(self, requirement: str, annotation: str = "", error_info: str = "") -> Optional[str]:
        """
        根据需求生成代码
        
        Args:
            requirement: 自然语言需求
            annotation: 实现注释
            error_info: 错误信息（用于修复）
            
        Returns:
            生成的Python代码
        """
        LogUtils.log_info("开始生成代码...")
        
        try:
            code_prompt = self._load_prompt_template("code")
            
            # 构建输入内容
            input_content = f"需求: {requirement}"
            if annotation:
                input_content += f"\n实现注释: {annotation}"
            if error_info:
                input_content += f"\n错误信息: {error_info}"
            
            messages = [
                {"role": "system", "content": code_prompt},
                {"role": "user", "content": input_content}
            ]
            
            response = self.llm_client.call(messages)
            if not response:
                LogUtils.log_error("LLM调用失败")
                return None
            
            # 提取Python代码
            code = self._extract_python_code(response)
            if code:
                LogUtils.log_success("代码生成完成")
                return code
            else:
                LogUtils.log_warning("未找到有效的Python代码")
                return None
                
        except Exception as e:
            LogUtils.log_error(f"代码生成失败: {e}")
            return None
    
    def generate_code_quiet(self, requirement: str, annotation: str = "", error_info: str = "", quiet: bool = False) -> Optional[str]:
        """
        根据需求生成代码（支持安静模式）
        """
        if not quiet:
            LogUtils.log_info("开始生成代码...")
        
        try:
            code_prompt = self._load_prompt_template("code")
            
            # 构建输入内容
            input_content = f"需求: {requirement}"
            if annotation:
                input_content += f"\n实现注释: {annotation}"
            if error_info:
                input_content += f"\n错误信息: {error_info}"
            
            messages = [
                {"role": "system", "content": code_prompt},
                {"role": "user", "content": input_content}
            ]
            
            response = self.llm_client.call(messages)
            if not response:
                if not quiet:
                    LogUtils.log_error("LLM调用失败")
                return None
            
            # 提取Python代码
            code = self._extract_python_code(response)
            if code:
                if not quiet:
                    LogUtils.log_success("代码生成完成")
                return code
            else:
                if not quiet:
                    LogUtils.log_warning("未找到有效的Python代码")
                return None
                
        except Exception as e:
            if not quiet:
                LogUtils.log_error(f"代码生成失败: {e}")
            return None
    
    def generate_test_cases(self, requirement: str, code: str = "", num_cases: int = 10) -> List[Dict[str, str]]:
        """
        生成测试用例
        
        Args:
            requirement: 自然语言需求
            code: 已生成的代码（可选）
            num_cases: 生成的测试用例数量
            
        Returns:
            测试用例列表
        """
        LogUtils.log_info(f"开始生成 {num_cases} 个测试用例...")
        
        try:
            case_prompt = self._load_prompt_template("case")
            
            # 构建输入内容
            input_content = f"用户的自然语言需求: {requirement}\n"
            if code:
                input_content += f"已生成的 Python 代码:\n```python\n{code}\n```\n"
            input_content += f"生成数量: {num_cases}"
            
            messages = [
                {"role": "system", "content": case_prompt},
                {"role": "user", "content": input_content}
            ]
            
            response = self.llm_client.call(messages)
            if not response:
                LogUtils.log_error("LLM调用失败")
                return []
            
            # 提取测试用例
            test_cases = self._extract_test_cases(response)
            LogUtils.log_success(f"生成了 {len(test_cases)} 个测试用例")
            return test_cases
            
        except Exception as e:
            LogUtils.log_error(f"测试用例生成失败: {e}")
            return []
    
    def generate_test_cases_quiet(self, requirement: str, code: str = "", num_cases: int = 10, quiet: bool = False) -> List[Dict[str, str]]:
        """
        生成测试用例（支持安静模式）
        """
        if not quiet:
            LogUtils.log_info(f"开始生成 {num_cases} 个测试用例...")
        
        try:
            case_prompt = self._load_prompt_template("case")
            
            # 构建输入内容
            input_content = f"用户的自然语言需求: {requirement}\n"
            if code:
                input_content += f"已生成的 Python 代码:\n```python\n{code}\n```\n"
            input_content += f"生成数量: {num_cases}"
            
            messages = [
                {"role": "system", "content": case_prompt},
                {"role": "user", "content": input_content}
            ]
            
            response = self.llm_client.call(messages)
            if not response:
                if not quiet:
                    LogUtils.log_error("LLM调用失败")
                return []
            
            # 提取测试用例
            test_cases = self._extract_test_cases(response)
            if not quiet:
                LogUtils.log_success(f"生成了 {len(test_cases)} 个测试用例")
            return test_cases
            
        except Exception as e:
            if not quiet:
                LogUtils.log_error(f"测试用例生成失败: {e}")
            return []
    
    def _extract_python_code(self, response: str) -> Optional[str]:
        """从响应中提取Python代码"""
        # 查找```python代码块
        python_pattern = r'```python\s*(.*?)\s*```'
        matches = re.findall(python_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # 如果没找到，尝试查找普通代码块
        code_pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        return None
    
    def _extract_test_cases(self, response: str) -> List[Dict[str, str]]:
        """从响应中提取测试用例"""
        try:
            # 尝试直接解析JSON
            data = json.loads(response)
            if "test_cases" in data:
                return data["test_cases"]
        except json.JSONDecodeError:
            pass
        
        # 尝试从代码块中提取JSON
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if "test_cases" in data:
                    return data["test_cases"]
            except json.JSONDecodeError:
                continue
        
        # 使用公共工具提取JSON
        json_str = JSONProcessor.extract_json_string(response)
        if json_str:
            try:
                data = json.loads(json_str)
                if "test_cases" in data:
                    return data["test_cases"]
            except json.JSONDecodeError:
                pass
        
        return []
    
    def process_subprompt_for_code_generation(self, subprompt: Dict[str, Any], quiet: bool = False) -> Dict[str, Any]:
        """
        处理单个子提示词，生成代码
        
        Args:
            subprompt: 子提示词字典，包含name、prompt等字段
            quiet: 是否使用安静模式（减少日志输出），默认False
            
        Returns:
            处理结果，包含代码、测试用例等
        """
        name = subprompt.get("name", "未命名子系统")
        prompt_content = subprompt.get("prompt", "")
        
        if not quiet:
            LogUtils.log_info(f"开始为子系统 '{name}' 生成代码")
        
        result = {
            "name": name,
            "original_prompt": prompt_content,
            "is_implementable": False,
            "code": None,
            "test_cases": [],
            "error": None
        }
        
        try:
            # 1. 判断可实现性
            judgment = self.judge_implementability_quiet(prompt_content, quiet)
            result["is_implementable"] = judgment.get("is_implementable", False)
            result["annotation"] = judgment.get("annotation", "")
            result["reason"] = judgment.get("reason", "")
            
            if not result["is_implementable"]:
                if not quiet:
                    LogUtils.log_warning(f"子系统 '{name}' 不适合代码实现: {result['reason']}")
                return result
            
            # 2. 生成代码
            code = self.generate_code_quiet(prompt_content, result["annotation"], quiet)
            if code:
                result["code"] = code
                if not quiet:
                    LogUtils.log_success(f"为子系统 '{name}' 生成代码成功")
                
                # 3. 生成测试用例
                test_cases = self.generate_test_cases_quiet(prompt_content, code, 5, quiet)
                result["test_cases"] = test_cases
                
            else:
                result["error"] = "代码生成失败"
                if not quiet:
                    LogUtils.log_error(f"为子系统 '{name}' 生成代码失败")
                
        except Exception as e:
            result["error"] = f"处理异常: {e}"
            if not quiet:
                LogUtils.log_error(f"处理子系统 '{name}' 时出错: {e}")
        
        return result
    
    def batch_process_subprompts(self, subprompts_data: Dict[str, Any], parallel: bool = True, max_workers: int = 5) -> Dict[str, Any]:
        """
        批量处理子提示词，为每个生成代码（支持并行处理）
        
        Args:
            subprompts_data: 包含子提示词列表的字典
            parallel: 是否使用并行处理，默认True
            max_workers: 并行处理的最大线程数，默认3
            
        Returns:
            批量处理结果
        """
        LogUtils.log_step("批量代码生成", "开始为所有子系统生成代码")
        
        # 提取子提示词列表
        subprompts = subprompts_data.get("subprompts", [])
        if not subprompts:
            LogUtils.log_error("没有找到子提示词数据")
            return {"error": "没有找到子提示词数据", "results": []}
        
        LogUtils.log_info(f"找到 {len(subprompts)} 个子系统，开始生成代码")
        
        if parallel and len(subprompts) > 1:
            LogUtils.log_info(f"使用并行处理模式，最大线程数: {max_workers}")
            return self._batch_process_parallel(subprompts, subprompts_data, max_workers)
        else:
            LogUtils.log_info("使用串行处理模式")
            return self._batch_process_serial(subprompts, subprompts_data)
    
    def _batch_process_parallel(self, subprompts: List[Dict], subprompts_data: Dict[str, Any], max_workers: int) -> Dict[str, Any]:
        """
        并行批量处理子提示词
        """
        start_time = time.time()
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_index = {}
            for i, subprompt in enumerate(subprompts):
                future = executor.submit(self._process_single_subprompt_safe, subprompt, i)
                future_to_index[future] = i
            
            # 收集结果
            completed_count = 0
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                    completed_count += 1
                    
                    name = result.get("name", f"子系统{index+1}")
                    status = "✅成功" if result.get("code") else ("⚠️可实现但生成失败" if result.get("is_implementable") else "❌不适合")
                    LogUtils.log_info(f"完成 {completed_count}/{len(subprompts)}: {name} - {status}")
                    
                except Exception as e:
                    LogUtils.log_error(f"处理子系统 {index+1} 时出现异常: {e}")
                    results[index] = {
                        "name": f"子系统{index+1}",
                        "original_prompt": subprompts[index].get("prompt", ""),
                        "is_implementable": False,
                        "code": None,
                        "test_cases": [],
                        "error": f"处理异常: {e}"
                    }
        
        # 按索引顺序整理结果
        ordered_results = [results.get(i, {}) for i in range(len(subprompts))]
        
        # 统计结果
        implementable_count = sum(1 for r in ordered_results if r.get("is_implementable", False))
        successful_count = sum(1 for r in ordered_results if r.get("code") is not None)
        
        processing_time = time.time() - start_time
        
        summary = {
            "total_subprompts": len(subprompts),
            "implementable_count": implementable_count,
            "successful_count": successful_count,
            "failed_count": len(subprompts) - successful_count,
            "processing_time": round(processing_time, 2),
            "parallel_processing": True
        }
        
        LogUtils.log_success(f"并行批量代码生成完成，耗时: {processing_time:.2f}秒")
        LogUtils.log_info(f"统计: {successful_count}/{implementable_count}/{len(subprompts)} (成功/可实现/总数)")
        
        return {
            "results": ordered_results,
            "summary": summary,
            "original_subprompts": subprompts_data
        }
    
    def _batch_process_serial(self, subprompts: List[Dict], subprompts_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        串行批量处理子提示词（原有逻辑）
        """
        start_time = time.time()
        results = []
        implementable_count = 0
        successful_count = 0
        
        for i, subprompt in enumerate(subprompts, 1):
            LogUtils.log_info(f"处理第 {i}/{len(subprompts)} 个子系统")
            result = self.process_subprompt_for_code_generation(subprompt)
            results.append(result)
            
            if result["is_implementable"]:
                implementable_count += 1
                if result["code"]:
                    successful_count += 1
        
        processing_time = time.time() - start_time
        
        summary = {
            "total_subprompts": len(subprompts),
            "implementable_count": implementable_count,
            "successful_count": successful_count,
            "failed_count": len(subprompts) - successful_count,
            "processing_time": round(processing_time, 2),
            "parallel_processing": False
        }
        
        LogUtils.log_success(f"串行批量代码生成完成，耗时: {processing_time:.2f}秒")
        LogUtils.log_info(f"统计: {successful_count}/{implementable_count}/{len(subprompts)} (成功/可实现/总数)")
        
        return {
            "results": results,
            "summary": summary,
            "original_subprompts": subprompts_data
        }
    
    def _process_single_subprompt_safe(self, subprompt: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        安全地处理单个子提示词（用于并行处理）
        """
        try:
            # 为并行处理添加简化的日志
            name = subprompt.get("name", f"子系统{index+1}")
            result = self.process_subprompt_for_code_generation(subprompt, quiet=True)
            return result
        except Exception as e:
            LogUtils.log_error(f"处理子系统 '{name}' 时出现异常: {e}")
            return {
                "name": name,
                "original_prompt": subprompt.get("prompt", ""),
                "is_implementable": False,
                "code": None,
                "test_cases": [],
                "error": f"处理异常: {e}"
            }
    
    def save_code_generation_results(self, results: Dict[str, Any], output_dir: str = "gen_code/output") -> bool:
        """
        保存代码生成结果
        
        Args:
            results: 代码生成结果
            output_dir: 输出目录
            
        Returns:
            是否保存成功
        """
        try:
            import os
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存完整结果
            result_file = os.path.join(output_dir, "code_generation_results.json")
            if not FileUtils.save_json(result_file, results):
                return False
            
            # 为每个成功的子系统保存单独的代码文件
            for i, result in enumerate(results.get("results", [])):
                if result.get("code"):
                    name = result["name"].replace(" ", "_").replace("/", "_")
                    code_file = os.path.join(output_dir, f"{name}_{i+1}.py")
                    
                    code_content = f'''"""
{result["name"]} - 自动生成的代码
原始需求: {result["original_prompt"][:100]}...
"""

{result["code"]}
'''
                    if not FileUtils.save_file(code_file, code_content):
                        LogUtils.log_warning(f"保存代码文件失败: {code_file}")
            
            LogUtils.log_success(f"代码生成结果已保存到 {output_dir}")
            return True
            
        except Exception as e:
            LogUtils.log_error(f"保存代码生成结果失败: {e}")
            return False 