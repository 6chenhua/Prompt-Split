"""
运算处理子系统 - 自动生成的代码
原始需求: 支持加减乘除四种运算，返回计算结果，处理除零错误...
"""

def calculate(num1, num2, operator):
    if operator == '+':
        return num1 + num2
    elif operator == '-':
        return num1 - num2
    elif operator == '*':
        return num1 * num2
    elif operator == '/':
        try:
            return num1 / num2
        except ZeroDivisionError:
            return "错误：除数不能为零"
    else:
        return "错误：不支持的运算符"
