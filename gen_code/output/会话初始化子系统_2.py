"""
会话初始化子系统 - 自动生成的代码
原始需求: 2. 说话人判断 - 明确每条消息是谁说的：客户经理（你）或博主（对方）。 - 禁止将自己代入博主立场作答。...
"""

def classify_speaker(message):
    """
    根据输入消息文本判断说话人是客户经理还是博主
    
    参数:
        message (str): 待分类的消息文本
        
    返回:
        str: "客户经理" 或 "博主"
    """
    # 简单关键词规则分类（实际应用中应替换为训练好的模型预测）
    manager_keywords = {"您好", "客户", "产品", "服务", "咨询", "方案", "报价", "合作"}
    blogger_keywords = {"大家好", "分享", "体验", "推荐", "测评", "个人", "觉得", "认为"}
    
    message_lower = message.lower()
    manager_score = sum(1 for kw in manager_keywords if kw in message_lower)
    blogger_score = sum(1 for kw in blogger_keywords if kw in message_lower)
    
    # 规则判断逻辑
    if manager_score > blogger_score:
        return "客户经理"
    elif blogger_score > manager_score:
        return "博主"
    else:
        # 当关键词得分相同时，默认返回客户经理（可根据实际数据调整）
        return "客户经理"
