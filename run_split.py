import json
import os
import re
from typing import Dict, Any

# 导入现有的功能模块
from extract_variable import process_chunks_concurrently, split_text_by_length, post_process
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


class PromptSplitPipeline:
    """
    提示词拆分流程编排器
    直接调用现有函数，专注于流程控制
    """
    
    def __init__(self):
        pass
    
    def read_file(self, file_path: str) -> str:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"❌ 文件 {file_path} 不存在")
            return ""
        except Exception as e:
            print(f"❌ 读取文件 {file_path} 时出错: {e}")
            return ""
    
    def save_file(self, file_path: str, content: str):
        """保存文件内容"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已保存到 {file_path}")
        except Exception as e:
            print(f"❌ 保存文件 {file_path} 时出错: {e}")
    
    def save_json(self, file_path: str, data: Dict):
        """保存JSON数据"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 已保存JSON到 {file_path}")
        except Exception as e:
            print(f"❌ 保存JSON文件 {file_path} 时出错: {e}")
    
    def step1_extract_variables(self, original_text: str) -> Dict[str, Any]:
        """
        第一步：提取变量
        调用 extract_variable.py 中的现有函数
        """
        print("=" * 50)
        print("🔍 第一步：开始提取变量...")
        
        if not original_text:
            return {"error": "输入文本为空"}
        
        try:
            # 使用现有的文本分割函数
            chunks = split_text_by_length(original_text)
            print(f"📄 文本已切割为 {len(chunks)} 个块")
            
            # 使用现有的并发处理函数提取变量
            variables = process_chunks_concurrently(chunks)
            print(f"🎯 提取到 {len(variables)} 个变量: {variables}")
            
            # 将变量标记到原文中
            text_with_vars = original_text
            for var in variables:
                text_with_vars = text_with_vars.replace(var, "{" + var + "}")
            
            # 使用现有的后处理函数
            try:
                processed_text = post_process(text_with_vars)
                print("✨ 变量后处理完成")
            except Exception as e:
                print(f"⚠️ 后处理失败，使用原始标记文本: {e}")
                processed_text = text_with_vars
            
            result = {
                "variables": variables,
                "original_text": original_text,
                "text_with_vars": processed_text,
                "chunks_count": len(chunks)
            }
            
            print(f"✅ 第一步完成，提取到 {len(variables)} 个变量")
            return result
            
        except Exception as e:
            error_msg = f"变量提取失败: {e}"
            print(f"❌ {error_msg}")
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
            response = llm_client.call(messages, "gpt-5-mini")
            
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
            response = llm_client.call(messages, "gpt-5-mini")
            
            # 提取JSON格式的子系统信息
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                subsystems_data = json.loads(json_match.group(0))
                return subsystems_data
            else:
                print("⚠️ 未找到JSON格式的子系统信息")
                return {"subsystems": []}
                
        except Exception as e:
            print(f"❌ 子系统拆分失败: {e}")
            return {"subsystems": []}
    
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
            response = llm_client.call(messages, "gpt-5-mini")
            
            # 提取JSON格式的子提示词信息
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                subprompts_data = json.loads(json_match.group(0))
                return subprompts_data
            else:
                print("⚠️ 未找到JSON格式的子提示词信息")
                return {"subprompts": []}
                
        except Exception as e:
            print(f"❌ 子提示词生成失败: {e}")
            return {"subprompts": []}
    
    def step2_split_to_subprompts(self, text_with_vars: str) -> Dict[str, Any]:
        """
        第二步：拆分为子提示词
        按照first_split.py的完整逻辑：mermaid生成 → 子系统拆分 → 子提示词生成
        """
        print("=" * 50)
        print("🔀 第二步：拆分为子提示词...")
        print("📊 按照完整流程：Mermaid生成 → 子系统拆分 → 子提示词生成")
        
        try:
            # 2.1 生成Mermaid流程图
            print("\n🎨 步骤2.1：生成Mermaid流程图...")
            mermaid_content = self.generate_mermaid_content(text_with_vars)
            if not mermaid_content:
                return {"error": "Mermaid图生成失败"}
            print("✅ Mermaid图生成完成")
            
            # 2.2 拆分为子系统
            print("\n🔧 步骤2.2：拆分为子系统...")
            subsystems_data = self.split_to_subsystems(mermaid_content)
            subsystems_count = len(subsystems_data.get("subsystems", []))
            if subsystems_count == 0:
                return {"error": "子系统拆分失败"}
            print(f"✅ 拆分出 {subsystems_count} 个子系统")
            
            # 2.3 生成子提示词
            print("\n📝 步骤2.3：生成子系统对应的提示词...")
            subprompts_data = self.generate_subprompts(text_with_vars, subsystems_data)
            subprompts_count = len(subprompts_data.get("subprompts", []))
            if subprompts_count == 0:
                return {"error": "子提示词生成失败"}
            print(f"✅ 生成了 {subprompts_count} 个子提示词")
            
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
            
            print(f"✅ 第二步完成")
            print(f"   - Mermaid图: 已生成")
            print(f"   - 子系统数量: {subsystems_count}")
            print(f"   - 子提示词数量: {subprompts_count}")
            
            return result
            
        except Exception as e:
            error_msg = f"拆分流程失败: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    def step3_convert_to_cnlp(self, subprompts_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        第三步：转换为CNLP格式
        调用 nl2cnlp.py 中的现有函数
        """
        print("=" * 50)
        print("🔄 第三步：转换为CNLP格式...")
        
        try:
            subprompts = subprompts_data.get("subprompts", {}).get("subprompts", [])
            if not subprompts:
                return {"error": "没有子提示词可转换"}
            
            print(f"🎯 开始转换 {len(subprompts)} 个子提示词...")
            
            # 使用现有的批量转换函数
            cnlp_results = batch_transform_cnlp(subprompts)
            
            # 过滤出成功转换的结果
            successful_results = []
            failed_count = 0
            
            for i, result in enumerate(cnlp_results):
                if result and result.strip():
                    successful_results.append({
                        "index": i,
                        "name": subprompts[i].get("name", f"子系统_{i+1}"),
                        "cnlp": result
                    })
                else:
                    failed_count += 1
                    print(f"⚠️ 子提示词 {i+1} 转换失败")
            
            result = {
                "cnlp_results": successful_results,
                "total_count": len(subprompts),
                "success_count": len(successful_results),
                "failed_count": failed_count,
                "original_subprompts": subprompts_data
            }
            
            print(f"✅ 第三步完成，成功转换 {len(successful_results)}/{len(subprompts)} 个子提示词")
            return result
            
        except Exception as e:
            error_msg = f"CNLP转换失败: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    def run_complete_pipeline(self, 
                             input_file: str = 'nl_prompt.txt',
                             save_intermediate: bool = True) -> Dict[str, Any]:
        """
        运行完整的拆分流程
        """
        print("🚀 开始运行完整的提示词拆分流程...")
        print(f"📝 输入文件: {input_file}")
        print("=" * 60)
        
        # 读取原始提示词
        original_text = self.read_file(input_file)
        if not original_text:
            return {"error": f"无法读取输入文件 {input_file}"}
        
        print(f"📊 原始文本长度: {len(original_text)} 字符")
        
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
        
        # 第三步：转换为CNLP
        step3_result = self.step3_convert_to_cnlp(step2_result)
        if "error" in step3_result:
            return step3_result
        
        if save_intermediate:
            self.save_json('output_step3_cnlp.json', step3_result)
        
        # 保存最终结果
        final_result = {
            "step1_variables": step1_result,
            "step2_split": step2_result,
            "step3_cnlp": step3_result,
            "summary": {
                "input_file": input_file,
                "variables_count": len(step1_result.get('variables', [])),
                "subsystems_count": step2_result.get('statistics', {}).get('subsystems_count', 0),
                "subprompts_count": step2_result.get('statistics', {}).get('subprompts_count', 0),
                "cnlp_success_count": step3_result.get('success_count', 0),
                "cnlp_failed_count": step3_result.get('failed_count', 0)
            }
        }
        
        if save_intermediate:
            self.save_json('output_final_result.json', final_result)
        
        print("=" * 60)
        print("🎉 完整流程执行完成！")
        print(f"📈 统计结果:")
        print(f"   - 提取变量数量: {final_result['summary']['variables_count']}")
        print(f"   - 子系统数量: {final_result['summary']['subsystems_count']}")
        print(f"   - 子提示词数量: {final_result['summary']['subprompts_count']}")
        print(f"   - CNLP转换成功: {final_result['summary']['cnlp_success_count']}")
        print(f"   - CNLP转换失败: {final_result['summary']['cnlp_failed_count']}")
        print("\n📁 输出文件:")
        print("   - output_step1_variables.json: 变量提取结果")
        print("   - output_step1_text_with_vars.txt: 标记变量的文本")
        print("   - output_step2_split.json: 完整拆分结果")
        print("   - output_step2_mermaid.txt: Mermaid流程图")
        print("   - output_step3_cnlp.json: CNLP转换结果")
        print("   - output_final_result.json: 完整结果")
        
        return final_result


def main():
    """主函数 - 简洁的流程控制"""
    print("🎯 提示词拆分系统 - 流程编排器")
    print("=" * 60)
    
    # 创建流程编排器实例
    pipeline = PromptSplitPipeline()
    
    # 运行完整流程
    result = pipeline.run_complete_pipeline(
        input_file='nl_prompt.txt',
        save_intermediate=True
    )
    
    if "error" in result:
        print(f"❌ 执行失败: {result['error']}")
        return False
    else:
        print("✅ 所有步骤执行成功！")
        return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1) 