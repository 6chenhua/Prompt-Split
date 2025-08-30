"""
输入与验证子系统 - 自动生成的代码
原始需求: 接收两个数字和一个运算符，输入：数字1，运算符，数字2，验证用户输入的数字和运算符是否有效...
"""

def is_valid_input(user_input):
    # 接收用户输入并按逗号分割为三个部分
    parts = user_input.split(',')
    
    # 验证分割后是否有三个元素
    if len(parts) != 3:
        return False
    
    num1_str, operator, num2_str = parts
    
    # 尝试将第一和第三部分转换为数字
    try:
        float(num1_str.strip())
        float(num2_str.strip())
    except ValueError:
        return False
    
    # 检查第二部分是否为允许的运算符
    allowed_operators = {'+', '-', '*', '/'}
    if operator.strip() not in allowed_operators:
        return False
    
    # 所有验证通过
    return True
