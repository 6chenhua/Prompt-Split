"""
用户问题处理子系统 - 自动生成的代码
原始需求: 【全局约束】-如果客户提出问题，先正面回答，再推进需求收集或项目规划。-客户若提出问题，需 先回答问题，再引导需求信息收集或预算沟通。-当客户提出直接问题（尤其是“{投放总预算}是多少”“{达人单价}...
"""

def is_question(user_input):
    """判断用户输入是否为问题"""
    question_words = ["什么", "为什么", "怎么", "哪里", "谁", "多少", "如何", "是否", "会不会"]
    if user_input.strip().endswith("?"):
        return True
    for word in question_words:
        if word in user_input:
            return True
    return False

def generate_answer(user_input):
    """根据用户问题生成回答"""
    if "投放总预算" in user_input:
        return "投放总预算会根据您的具体需求、目标受众和推广周期来定制，我们会提供多种方案供您选择。"
    elif "达人单价" in user_input:
        return "达人单价因达人粉丝量、影响力、内容质量等因素而异，我们有不同层级的达人资源可以匹配您的需求。"
    else:
        return "感谢您的提问，我们会根据您的具体需求提供详细解答。"

def guide_requirement_collection(user_input):
    """引导需求收集或项目规划"""
    if "投放总预算" in user_input or "达人单价" in user_input:
        return "为了给您提供更精准的方案，能否请您先告诉我们您的推广目标和预期效果？"
    else:
        return "接下来，我们可以详细讨论您的项目需求，或者您希望了解我们的哪些服务内容？"

def process_customer_conversation(user_input):
    """处理客户对话的主函数"""
    response = []
    if is_question(user_input):
        # 生成回答
        answer = generate_answer(user_input)
        response.append(answer)
        # 生成引导语
        guide = guide_requirement_collection(user_input)
        response.append(guide)
    else:
        # 如果不是问题，直接进入需求收集
        guide = guide_requirement_collection(user_input)
        response.append(guide)
    
    return "\n".join(response)
