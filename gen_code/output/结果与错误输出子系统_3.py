"""
结果与错误输出子系统 - 自动生成的代码
原始需求: 输出：计算结果或错误信息...
"""

def calculate_result(a, b):
    try:
        result = a / b
        return result
    except ZeroDivisionError:
        return "错误信息：除数不能为零"
    except TypeError:
        return "错误信息：输入必须是数字类型"
