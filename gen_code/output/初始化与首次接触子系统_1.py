"""
初始化与首次接触子系统 - 自动生成的代码
原始需求: 【前置动作】1. 读取信息 - 聊天历史记录：{outputList} - 当前客户消息：{input} - {产品名称}：{product} 2. 说话人判断 - 明确每条消息是谁说的：客户经理（你...
"""

def process_chat_context(outputList, input, product):
    """处理聊天上下文，确保仅以客户经理立场生成内容"""
    # 定义数据结构存储聊天信息
    chat_data = {
        'history': outputList,
        'current_message': input,
        'product': product,
        'valid_senders': ['客户经理', '博主']
    }
    
    # 验证聊天历史记录格式并筛选有效发送者
    for msg in chat_data['history']:
        if not isinstance(msg, dict) or 'sender' not in msg or 'message' not in msg:
            raise ValueError("聊天记录格式错误，需包含'sender'和'message'字段")
        
        sender = msg['sender']
        if sender not in chat_data['valid_senders']:
            raise ValueError(f"无效发送者: {sender}，仅支持{chat_data['valid_senders']}")
    
    # 分离不同角色的消息
    客户经理_messages = [msg for msg in chat_data['history'] if msg['sender'] == '客户经理']
    博主_messages = [msg for msg in chat_data['history'] if msg['sender'] == '博主']
    
    # 返回处理结果，明确标识客户经理立场
    return {
        'customer_service_history': 客户经理_messages,
        'blogger_history': 博主_messages,
        'current_query': chat_data['current_message'],
        'product_name': chat_data['product'],
        'response_perspective': '客户经理'
    }
