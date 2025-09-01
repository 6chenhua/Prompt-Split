"""
修复编码问题的工具脚本
解决在代码生成过程中可能遇到的UnicodeDecodeError问题
"""

import subprocess
import sys
import locale
import os
from typing import Tuple, Optional

def detect_system_encoding():
    """检测系统编码环境"""
    print("🔍 检测系统编码环境...")
    
    # 检测系统默认编码
    default_encoding = locale.getpreferredencoding()
    print(f"   系统默认编码: {default_encoding}")
    
    # 检测标准输出编码
    stdout_encoding = sys.stdout.encoding
    print(f"   标准输出编码: {stdout_encoding}")
    
    # 检测文件系统编码
    fs_encoding = sys.getfilesystemencoding()
    print(f"   文件系统编码: {fs_encoding}")
    
    # 检测环境变量
    pythonioencoding = os.environ.get('PYTHONIOENCODING', '未设置')
    print(f"   PYTHONIOENCODING: {pythonioencoding}")
    
    return {
        'default': default_encoding,
        'stdout': stdout_encoding,
        'filesystem': fs_encoding,
        'pythonioencoding': pythonioencoding
    }

def test_subprocess_encoding(test_code: str = "print('Hello, 中文测试')") -> Tuple[bool, str]:
    """测试subprocess的编码处理"""
    print(f"\n🧪 测试subprocess编码处理...")
    print(f"   测试代码: {test_code}")
    
    encodings_to_test = ["utf-8", "gbk", "gb2312", "cp936", "latin-1"]
    
    for encoding in encodings_to_test:
        try:
            print(f"   尝试编码: {encoding}")
            result = subprocess.run(
                ["python", "-c", test_code],
                capture_output=True,
                text=True,
                encoding=encoding,
                errors='replace',
                timeout=5
            )
            
            if result.returncode == 0:
                print(f"   ✅ {encoding} 编码成功")
                print(f"      输出: {repr(result.stdout.strip())}")
                return True, encoding
            else:
                print(f"   ❌ {encoding} 执行失败: {result.stderr}")
                
        except UnicodeDecodeError as e:
            print(f"   ❌ {encoding} 编码错误: {e}")
        except Exception as e:
            print(f"   ❌ {encoding} 其他错误: {e}")
    
    return False, "所有编码都失败"

def test_bytes_mode(test_code: str = "print('Hello, 中文测试')") -> Tuple[bool, str]:
    """测试bytes模式的subprocess"""
    print(f"\n🔧 测试bytes模式处理...")
    
    try:
        result = subprocess.run(
            ["python", "-c", test_code],
            capture_output=True,
            timeout=5
        )
        
        # 手动处理编码
        stdout = ""
        stderr = ""
        
        if result.stdout:
            for encoding in ["utf-8", "gbk", "gb2312", "cp936"]:
                try:
                    stdout = result.stdout.decode(encoding)
                    print(f"   ✅ stdout解码成功 ({encoding}): {repr(stdout.strip())}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                stdout = result.stdout.decode('utf-8', errors='replace')
                print(f"   ⚠️ stdout使用替换模式解码: {repr(stdout.strip())}")
        
        if result.stderr:
            for encoding in ["utf-8", "gbk", "gb2312", "cp936"]:
                try:
                    stderr = result.stderr.decode(encoding)
                    print(f"   stderr解码成功 ({encoding}): {repr(stderr.strip())}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                stderr = result.stderr.decode('utf-8', errors='replace')
                print(f"   stderr使用替换模式解码: {repr(stderr.strip())}")
        
        return True, "bytes模式成功"
        
    except Exception as e:
        print(f"   ❌ bytes模式失败: {e}")
        return False, str(e)

def fix_environment():
    """尝试修复环境设置"""
    print("\n🔧 尝试修复环境设置...")
    
    # 设置环境变量
    fixes_applied = []
    
    if not os.environ.get('PYTHONIOENCODING'):
        os.environ['PYTHONIOENCODING'] = 'utf-8:replace'
        fixes_applied.append('设置 PYTHONIOENCODING=utf-8:replace')
    
    if not os.environ.get('PYTHONLEGACYWINDOWSSTDIO'):
        os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
        fixes_applied.append('设置 PYTHONLEGACYWINDOWSSTDIO=1')
    
    if fixes_applied:
        print("   应用的修复:")
        for fix in fixes_applied:
            print(f"   - {fix}")
        return True
    else:
        print("   无需修复环境变量")
        return False

def create_safe_subprocess_function():
    """创建安全的subprocess函数"""
    code = '''
def safe_run_code(code: str, input_code: str = None) -> Tuple[Optional[str], Optional[str]]:
    """
    安全运行Python代码的函数，解决编码问题
    """
    import subprocess
    import sys
    import os
    from typing import Tuple, Optional
    
    full_code = code
    if input_code:
        full_code += f"\\n\\n{input_code}"
    
    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8:replace'
    env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
    
    try:
        # 首先尝试text模式
        result = subprocess.run(
            [sys.executable, "-c", full_code],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=10,
            env=env
        )
        
        if result.returncode != 0:
            return None, result.stderr.strip()
        return result.stdout.strip(), None
        
    except Exception as text_error:
        try:
            # 回退到bytes模式
            result = subprocess.run(
                [sys.executable, "-c", full_code],
                capture_output=True,
                timeout=10,
                env=env
            )
            
            # 手动处理编码
            stdout = ""
            stderr = ""
            
            if result.stdout:
                try:
                    stdout = result.stdout.decode('utf-8', errors='replace')
                except:
                    stdout = str(result.stdout)
            
            if result.stderr:
                try:
                    stderr = result.stderr.decode('utf-8', errors='replace')
                except:
                    stderr = str(result.stderr)
            
            if result.returncode != 0:
                return None, stderr.strip()
            return stdout.strip(), None
            
        except Exception as bytes_error:
            return None, f"执行异常: text_mode={text_error}, bytes_mode={bytes_error}"
'''
    
    print(f"\n📝 生成安全的subprocess函数代码:")
    print("=" * 60)
    print(code)
    print("=" * 60)
    
    return code

def main():
    """主函数"""
    print("🔧 编码问题修复工具")
    print("=" * 50)
    
    # 检测系统编码
    encoding_info = detect_system_encoding()
    
    # 测试subprocess编码
    success, result = test_subprocess_encoding()
    if not success:
        print(f"\n⚠️ 标准编码测试失败: {result}")
        
        # 尝试修复环境
        fix_environment()
        
        # 重新测试
        success, result = test_subprocess_encoding()
        if success:
            print(f"\n✅ 环境修复后测试成功: {result}")
        else:
            print(f"\n❌ 环境修复后仍然失败: {result}")
            
            # 测试bytes模式
            bytes_success, bytes_result = test_bytes_mode()
            if bytes_success:
                print(f"\n✅ bytes模式可以工作: {bytes_result}")
            else:
                print(f"\n❌ bytes模式也失败: {bytes_result}")
    else:
        print(f"\n✅ 编码测试成功: {result}")
    
    # 生成安全函数
    safe_function_code = create_safe_subprocess_function()
    
    print(f"\n💡 建议:")
    print("1. 在Windows系统上，建议设置环境变量：")
    print("   - PYTHONIOENCODING=utf-8:replace")  
    print("   - PYTHONLEGACYWINDOWSSTDIO=1")
    print("2. 使用上面生成的safe_run_code函数替换现有的run_code方法")
    print("3. 确保生成的代码不包含特殊字符")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 