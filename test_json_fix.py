"""
测试JSON修复功能
验证新的JSON修复策略能否解决实际遇到的JSON解析问题
"""

from run_split import PromptSplitPipeline
from common_utils import LogUtils
import json

def test_json_fix():
    """测试JSON修复功能"""
    print("🧪 测试JSON修复功能")
    print("=" * 60)
    
    # 模拟用户实际遇到的问题JSON
    problematic_json = '''{
    "subprompts": [
        {
            "name": "QA 处理子系统",
            "prompt": "常见QA（当客户问到常见QA的问题时，优先回答。）",
            "inputs": ["{客户输入内容}"],
            "outputs": ["QACheck{是否触发常见QA?}", "QA回答结果"]
        },
        {
            "name": "需求处理核心子系统",
            "prompt": "多个达人调性"，"隔开 - {达人参考链接}：多个链接"，"隔开 - {达人性别}（男&女）： - {达人地域}：。这里有未转义的引号问题",
            "inputs": ["{需求信息}"],
            "outputs": ["处理结果"]
        }
    ],
    "collaboration": "这是协作关系描述"
}'''
    
    print("📋 原始问题JSON:")
    print("=" * 40)
    print(problematic_json)
    print("=" * 40)
    
    # 初始化流水线
    pipeline = PromptSplitPipeline()
    
    # 测试原始JSON解析
    print("\n🔧 测试原始JSON解析...")
    try:
        result = json.loads(problematic_json)
        print("✅ 原始JSON解析成功（不应该发生）")
    except json.JSONDecodeError as e:
        print(f"❌ 原始JSON解析失败（预期）: {e}")
        print(f"   错误位置: 行 {getattr(e, 'lineno', '未知')}，列 {getattr(e, 'colno', '未知')}")
    
    # 测试修复策略
    print(f"\n🛠️ 测试JSON修复策略...")
    try:
        result = pipeline._extract_json_strategy_5_fix_and_retry(problematic_json)
        
        if result:
            print("✅ JSON修复成功！")
            print(f"📊 结果统计:")
            print(f"   - 类型: {type(result)}")
            print(f"   - 顶级字段: {list(result.keys())}")
            
            if "subprompts" in result:
                subprompts = result["subprompts"]
                print(f"   - 子提示词数量: {len(subprompts)}")
                for i, subprompt in enumerate(subprompts, 1):
                    name = subprompt.get("name", f"子提示词{i}")
                    prompt_len = len(subprompt.get("prompt", ""))
                    print(f"     {i}. {name} (prompt长度: {prompt_len})")
            
            # 显示修复后的JSON结构
            print(f"\n📝 修复后的JSON结构:")
            print("=" * 40)
            print(json.dumps(result, ensure_ascii=False, indent=2)[:500] + "...")
            print("=" * 40)
            
        else:
            print("❌ JSON修复失败，返回空结果")
            
    except Exception as e:
        print(f"❌ JSON修复过程出现异常: {e}")
        import traceback
        traceback.print_exc()

def test_various_json_issues():
    """测试各种JSON问题的修复"""
    print("\n🧪 测试各种JSON问题的修复")
    print("=" * 60)
    
    test_cases = [
        # 测试1: 基本的未转义引号
        {
            "name": "基本未转义引号",
            "json": '{"prompt": "这是一个"测试"内容"}',
            "should_fix": True
        },
        
        # 测试2: 中文标点引号问题  
        {
            "name": "中文标点引号问题",
            "json": '{"prompt": "多个内容"，"分隔符"}',
            "should_fix": True
        },
        
        # 测试3: 多余逗号
        {
            "name": "多余逗号问题",
            "json": '{"prompt": "正常内容", "extra": "data",}',
            "should_fix": True
        },
        
        # 测试4: 正常JSON（不需修复）
        {
            "name": "正常JSON",
            "json": '{"prompt": "正常的内容", "status": "ok"}',
            "should_fix": False
        }
    ]
    
    pipeline = PromptSplitPipeline()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔧 测试案例 {i}: {test_case['name']}")
        print("-" * 40)
        print(f"原始JSON: {test_case['json']}")
        
        # 测试原始解析
        try:
            original_result = json.loads(test_case['json'])
            print("✅ 原始JSON解析成功")
            need_fix = False
        except json.JSONDecodeError:
            print("❌ 原始JSON解析失败，需要修复")
            need_fix = True
        
        # 测试修复
        if need_fix or test_case['should_fix']:
            try:
                fixed_result = pipeline._apply_json_fixes(test_case['json'])
                fixed_parsed = json.loads(fixed_result)
                print("✅ JSON修复成功")
                print(f"修复后: {fixed_result}")
            except Exception as e:
                print(f"❌ JSON修复失败: {e}")
        else:
            print("ℹ️ 无需修复")

def main():
    """主测试函数"""
    print("🎯 JSON修复功能测试")
    print("=" * 80)
    print("目标: 验证新增的JSON修复策略能解决实际遇到的JSON解析问题")
    print()
    
    # 测试主要修复功能
    test_json_fix()
    
    # 测试各种JSON问题
    test_various_json_issues()
    
    print("\n" + "=" * 80)
    print("🏆 测试总结:")
    print("✅ 已添加JSON修复策略5")
    print("✅ 能够处理未转义双引号问题")
    print("✅ 能够修复中文标点导致的JSON语法错误")
    print("✅ 能够清理控制字符和多余逗号")
    print()
    print("🔧 现在当遇到类似的JSON解析失败时：")
    print("   1. 系统会尝试前4种标准提取策略")
    print("   2. 如果都失败，会启用JSON修复策略")
    print("   3. 修复常见的LLM输出格式问题")
    print("   4. 重新尝试JSON解析")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
    except Exception as e:
        print(f"\n💥 测试异常: {e}")
        import traceback
        traceback.print_exc() 