"""
测试UI中Mermaid流程图功能
"""

import sys
import os

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_imports():
    """测试所需模块是否能正常导入"""
    print("🔍 测试模块导入...")
    
    try:
        from mermaid_generator import MermaidGenerator
        print("✅ MermaidGenerator 导入成功")
        
        from code_generator import CodeGenerator
        print("✅ CodeGenerator 导入成功")
        
        from run_split import PromptSplitPipeline
        print("✅ PromptSplitPipeline 导入成功")
        
        import streamlit as st
        print("✅ Streamlit 导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_mermaid_generation():
    """测试Mermaid生成功能"""
    print("\n🎨 测试Mermaid生成功能...")
    
    try:
        from mermaid_generator import MermaidGenerator
        
        # 创建测试数据
        test_data = {
            "subsystems": [
                {
                    "name": "用户输入处理",
                    "description": "负责接收和预处理用户输入",
                    "code": "def process_input(data): return data.strip()"
                },
                {
                    "name": "数据分析",
                    "description": "分析处理后的数据",
                    "cnlp": "使用自然语言处理分析数据意图"
                },
                {
                    "name": "结果输出",
                    "description": "格式化并输出结果",
                    "code": "def format_output(result): return str(result)",
                    "cnlp": "对输出进行自然语言解释"
                }
            ],
            "collaboration": "用户输入处理模块接收输入，传递给数据分析模块处理，最后由结果输出模块生成最终结果。"
        }
        
        generator = MermaidGenerator()
        mermaid_code = generator.generate_mermaid_diagram(test_data, quiet=True)
        
        if mermaid_code:
            print("✅ Mermaid代码生成成功")
            print(f"   代码长度: {len(mermaid_code)} 字符")
            
            # 验证语法
            is_valid, message = generator.validate_mermaid_syntax(mermaid_code)
            if is_valid:
                print(f"✅ 语法验证通过: {message}")
            else:
                print(f"❌ 语法验证失败: {message}")
                return False
            
            return True
        else:
            print("❌ Mermaid代码生成失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_code_generator_integration():
    """测试代码生成器集成"""
    print("\n🔧 测试代码生成器集成...")
    
    try:
        from code_generator import CodeGenerator
        
        # 模拟subsystems数据
        test_data = {
            "subsystems": [
                {
                    "name": "测试子系统",
                    "description": "用于测试的简单子系统",
                    "inputs": ["输入参数"],
                    "outputs": ["输出结果"],
                    "prompt": "创建一个简单的测试函数"
                }
            ],
            "collaboration": "这是一个测试用的简单协作关系。"
        }
        
        generator = CodeGenerator()
        
        # 测试mermaid生成器是否正确初始化
        if hasattr(generator, 'mermaid_generator'):
            print("✅ MermaidGenerator 已正确集成到 CodeGenerator")
            
            # 测试mermaid生成方法
            mermaid_code = generator.mermaid_generator.generate_mermaid_diagram(test_data, quiet=True)
            if mermaid_code:
                print("✅ 集成的Mermaid生成功能正常")
                return True
            else:
                print("❌ 集成的Mermaid生成功能异常")
                return False
        else:
            print("❌ MermaidGenerator 未正确集成到 CodeGenerator")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_config_settings():
    """测试配置设置"""
    print("\n⚙️ 测试配置设置...")
    
    try:
        import json
        
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查代码生成配置
        if 'step2_5_code_generation' in config:
            code_config = config['step2_5_code_generation']
            print("✅ 找到代码生成配置")
            
            if code_config.get('generate_mermaid', False):
                print("✅ Mermaid生成已启用")
                return True
            else:
                print("⚠️ Mermaid生成未启用，但配置存在")
                return True
        else:
            print("❌ 未找到代码生成配置")
            return False
            
    except Exception as e:
        print(f"❌ 配置测试异常: {e}")
        return False

def test_ui_components():
    """测试UI组件是否可以导入"""
    print("\n🖥️ 测试UI组件...")
    
    try:
        # 不直接运行streamlit，只测试函数定义
        import ui_streamlit
        
        # 检查新增的函数是否存在
        required_functions = [
            'render_flowchart_tab',
            'render_flowchart_legend', 
            'render_subsystem_overview'
        ]
        
        missing_functions = []
        for func_name in required_functions:
            if hasattr(ui_streamlit, func_name):
                print(f"✅ 函数 {func_name} 存在")
            else:
                print(f"❌ 函数 {func_name} 缺失")
                missing_functions.append(func_name)
        
        if not missing_functions:
            print("✅ 所有UI函数都已正确定义")
            return True
        else:
            print(f"❌ 缺失函数: {missing_functions}")
            return False
            
    except Exception as e:
        print(f"❌ UI组件测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 开始UI Mermaid功能测试")
    print("=" * 50)
    
    test_results = []
    
    # 运行所有测试
    test_results.append(("模块导入", test_imports()))
    test_results.append(("Mermaid生成", test_mermaid_generation()))
    test_results.append(("代码生成器集成", test_code_generator_integration()))
    test_results.append(("配置设置", test_config_settings()))
    test_results.append(("UI组件", test_ui_components()))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！UI Mermaid功能已准备就绪")
        print("\n💡 下一步:")
        print("   1. 运行 'python ui_streamlit.py' 启动界面")
        print("   2. 输入测试文本并开始处理")
        print("   3. 查看'🎨 系统流程图'选项卡")
    else:
        print("⚠️ 部分测试失败，请检查上述错误信息")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 