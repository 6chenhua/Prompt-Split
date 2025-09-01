"""
测试代码生成功能的脚本
"""

import os
import sys
from pathlib import Path
from run_split import PromptSplitPipeline
from common_utils import LogUtils

def test_code_generation_with_sample():
    """使用示例提示词测试代码生成功能"""
    
    # 示例提示词 - 一个简单的计算器功能
    sample_prompt = """
    你是一个数学计算助手，负责执行基本的数学运算。
    
    功能要求：
    1. 接收两个数字和一个运算符
    2. 支持加减乘除四种运算
    3. 返回计算结果
    4. 处理除零错误
    
    输入：数字1，运算符，数字2
    输出：计算结果或错误信息
    """
    
    LogUtils.log_step("代码生成测试", "开始测试代码生成功能")
    
    try:
        # 创建流水线
        pipeline = PromptSplitPipeline()
        
        # 第一步：提取变量
        LogUtils.log_info("步骤1: 提取变量")
        step1_result = pipeline.step1_extract_variables(sample_prompt)
        if "error" in step1_result:
            LogUtils.log_error(f"步骤1失败: {step1_result['error']}")
            return False
        
        LogUtils.log_success(f"提取到 {len(step1_result.get('variables', []))} 个变量")
        
        # 第二步：拆分子系统
        LogUtils.log_info("步骤2: 拆分子系统")
        step2_result = pipeline.step2_split_to_subprompts(step1_result['text_with_vars'])
        if "error" in step2_result:
            LogUtils.log_error(f"步骤2失败: {step2_result['error']}")
            return False
        
        subprompts_count = len(step2_result.get('subprompts', {}).get('subprompts', []))
        LogUtils.log_success(f"生成了 {subprompts_count} 个子提示词")
        
        # 第2.5步：代码生成（新功能）
        LogUtils.log_info("步骤2.5: 代码生成")
        step2_5_result = pipeline.step2_5_generate_code(step2_result)
        
        if "error" in step2_5_result and step2_5_result.get("results") is None:
            LogUtils.log_error(f"代码生成完全失败: {step2_5_result['error']}")
            return False
        
        # 分析代码生成结果
        results = step2_5_result.get("results", [])
        summary = step2_5_result.get("summary", {})
        
        LogUtils.log_info("代码生成结果分析:")
        LogUtils.log_info(f"  - 总子系统数: {summary.get('total_subprompts', 0)}")
        LogUtils.log_info(f"  - 可实现数: {summary.get('implementable_count', 0)}")
        LogUtils.log_info(f"  - 生成成功数: {summary.get('successful_count', 0)}")
        LogUtils.log_info(f"  - 生成失败数: {summary.get('failed_count', 0)}")
        
        # 显示每个子系统的代码生成情况
        for i, result in enumerate(results, 1):
            name = result.get("name", f"子系统{i}")
            is_implementable = result.get("is_implementable", False)
            has_code = result.get("code") is not None
            
            status = "✅成功" if has_code else ("⚠️可实现但生成失败" if is_implementable else "❌不适合代码实现")
            LogUtils.log_info(f"  {i}. {name}: {status}")
            
            if has_code:
                code = result["code"]
                LogUtils.log_info(f"     生成代码长度: {len(code)} 字符")
                test_cases = result.get("test_cases", [])
                LogUtils.log_info(f"     测试用例数量: {len(test_cases)}")
        
        # 保存结果
        LogUtils.log_info("保存测试结果...")
        
        # 保存到cache目录（使用当前时间戳）
        import time
        timestamp = int(time.time())
        cache_file = f"cache/test_code_generation_{timestamp}.json"
        
        # 确保cache目录存在
        os.makedirs("cache", exist_ok=True)
        
        test_result = {
            "step1_variables": step1_result,
            "step2_split": step2_result,
            "step2_5_code": step2_5_result,
            "test_summary": {
                "total_subprompts": summary.get('total_subprompts', 0),
                "implementable_count": summary.get('implementable_count', 0),
                "successful_count": summary.get('successful_count', 0),
                "failed_count": summary.get('failed_count', 0)
            }
        }
        
        if pipeline.save_json(cache_file, test_result):
            LogUtils.log_success(f"测试结果已保存到: {cache_file}")
        else:
            LogUtils.log_warning("保存测试结果失败")
        
        # 判断测试是否成功
        success_rate = summary.get('successful_count', 0) / max(summary.get('total_subprompts', 1), 1)
        if success_rate > 0:
            LogUtils.log_success(f"🎉 代码生成测试完成！成功率: {success_rate:.1%}")
            return True
        else:
            LogUtils.log_warning("⚠️ 代码生成测试完成，但没有成功生成任何代码")
            return False
            
    except Exception as e:
        LogUtils.log_error(f"测试过程中出现异常: {e}")
        return False

def main():
    """主函数"""
    LogUtils.log_step("代码生成功能测试", "开始验证代码生成功能是否正常工作")
    
    success = test_code_generation_with_sample()
    
    if success:
        LogUtils.log_success("✅ 代码生成功能测试通过！")
        print("\n" + "="*60)
        print("🎉 代码生成功能已成功融入项目！")
        print("现在您可以:")
        print("1. 运行 `python run_split.py` 使用完整流程")
        print("2. 运行 `streamlit run ui_streamlit.py` 使用Web界面")
        print("3. 在第二步生成子提示词后，会自动尝试生成代码")
        print("4. 生成的代码文件会保存在 gen_code/output/ 目录中")
        print("="*60)
        return True
    else:
        LogUtils.log_error("❌ 代码生成功能测试失败！")
        print("\n" + "="*60)
        print("⚠️ 代码生成功能可能存在问题，请检查:")
        print("1. API配置是否正确")
        print("2. 网络连接是否正常")
        print("3. LLM服务是否可用")
        print("="*60)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 