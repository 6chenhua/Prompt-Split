"""
测试Mermaid流程图生成功能
"""

import json
from mermaid_generator import MermaidGenerator
from code_generator import CodeGenerator
from common_utils import LogUtils

def test_mermaid_generation():
    """测试mermaid生成功能"""
    
    # 模拟子系统数据
    test_data = {
        "subsystems": [
            {
                "name": "输入预处理子系统",
                "description": "负责接收和预处理用户输入",
                "code": "def preprocess_input(data): return data.strip()"
            },
            {
                "name": "数据分析子系统", 
                "description": "分析处理后的数据",
                "cnlp": "使用自然语言处理分析数据意图和语义"
            },
            {
                "name": "结果输出子系统",
                "description": "格式化并输出最终结果",
                "code": "def format_output(result): return json.dumps(result)",
                "cnlp": "对输出结果进行自然语言解释"
            }
        ],
        "collaboration": "输入预处理子系统首先接收用户输入并进行标准化处理，然后将处理后的数据传递给数据分析子系统进行深度分析，最后由结果输出子系统将分析结果格式化并输出给用户。"
    }
    
    print("=== 测试Mermaid流程图生成 ===")
    
    # 测试单独的mermaid生成器
    print("\n1. 测试独立的Mermaid生成器...")
    mermaid_gen = MermaidGenerator()
    mermaid_code = mermaid_gen.generate_mermaid_diagram(test_data)
    
    if mermaid_code:
        print("✅ Mermaid生成成功!")
        print(f"生成的代码长度: {len(mermaid_code)} 字符")
        
        # 验证语法
        is_valid, message = mermaid_gen.validate_mermaid_syntax(mermaid_code)
        print(f"语法验证: {'✅ 通过' if is_valid else '❌ 失败'} - {message}")
        
        # 保存到文件
        save_success = mermaid_gen.save_mermaid_to_file(mermaid_code, "test_flowchart")
        print(f"文件保存: {'✅ 成功' if save_success else '❌ 失败'}")
        
        print("\n生成的Mermaid代码:")
        print("=" * 50)
        print(mermaid_code)
        print("=" * 50)
        
    else:
        print("❌ Mermaid生成失败")
    
    # 测试集成在代码生成器中的功能
    print("\n2. 测试集成的代码生成器...")
    code_gen = CodeGenerator()
    
    # 模拟批量处理
    result = code_gen.batch_process_subsystems(test_data, parallel=False, generate_mermaid=True)
    
    if "mermaid_diagram" in result:
        print("✅ 集成mermaid生成成功!")
        print(f"生成的代码长度: {len(result['mermaid_diagram'])} 字符")
    else:
        print("❌ 集成mermaid生成失败")
    
    return result

def test_edge_cases():
    """测试边缘情况"""
    print("\n=== 测试边缘情况 ===")
    
    mermaid_gen = MermaidGenerator()
    
    # 测试空数据
    print("\n1. 测试空数据...")
    empty_data = {"subsystems": [], "collaboration": ""}
    result = mermaid_gen.generate_mermaid_diagram(empty_data)
    print(f"空数据测试: {'❌ 符合预期' if result is None else '⚠️ 意外结果'}")
    
    # 测试缺少collaboration
    print("\n2. 测试缺少协作关系...")
    no_collab_data = {"subsystems": [{"name": "测试子系统"}]}
    result = mermaid_gen.generate_mermaid_diagram(no_collab_data)
    print(f"缺少协作关系测试: {'❌ 符合预期' if result is None else '⚠️ 意外结果'}")
    
    # 测试只有代码的子系统
    print("\n3. 测试只有代码的子系统...")
    code_only_data = {
        "subsystems": [
            {"name": "代码子系统1", "code": "def func1(): pass"},
            {"name": "代码子系统2", "code": "def func2(): pass"}
        ],
        "collaboration": "子系统1处理输入，子系统2处理输出"
    }
    result = mermaid_gen.generate_mermaid_diagram(code_only_data)
    print(f"只有代码子系统测试: {'✅ 成功' if result else '❌ 失败'}")

if __name__ == "__main__":
    try:
        # 主要功能测试
        result = test_mermaid_generation()
        
        # 边缘情况测试
        test_edge_cases()
        
        print("\n=== 测试完成 ===")
        print("查看生成的文件:")
        print("- gen_code/output/test_flowchart.md")
        print("- gen_code/output/system_flowchart.md")
        
    except Exception as e:
        LogUtils.log_error(f"测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc() 