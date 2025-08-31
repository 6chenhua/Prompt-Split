"""
QA处理子系统 - 自动生成的代码
原始需求: -如果客户提出{问题}，先正面回答，再推进{需求}收集或项目规划。-客户若提出{问题}，需 先回答{问题}，再引导{需求}信息收集或预算沟通。-当客户提出直接{问题}（尤其是“预算范围是多少”“达人单...
"""

def handle_customer_query(query):
    """处理客户问题，生成包含回答和需求引导的完整回复"""
    # 1. 定义问题分类规则
    direct_question_keywords = ["预算", "单价", "价格", "费用", "多少钱", "成本"]
    
    # 2. 构建回答模板与需求引导模板
    answer_templates = {
        "direct": "关于{topic}，我们需要根据具体需求来确定。",
        "general": "针对您的问题，我们有相应的解决方案。"
    }
    
    guidance_templates = {
        "direct": "为了给您更准确的{topic}信息，能否请您先提供项目的具体需求？",
        "general": "我们可以进一步沟通项目的具体需求和规划细节。"
    }
    
    # 3. 流程控制逻辑
    # 分类问题
    is_direct = any(keyword in query for keyword in direct_question_keywords)
    
    # 提取主题关键词
    topic = next((kw for kw in direct_question_keywords if kw in query), "相关")
    
    # 生成回答和引导内容
    answer = answer_templates["direct"].format(topic=topic) if is_direct else answer_templates["general"]
    guidance = guidance_templates["direct"].format(topic=topic) if is_direct else guidance_templates["general"]
    
    # 按规则组合输出
    return f"{answer} {guidance}"
