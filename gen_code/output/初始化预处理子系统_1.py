"""
初始化预处理子系统 - 自动生成的代码
原始需求: 1. 读取信息 - 聊天历史记录：{{{outputList}}} - 当前客户消息：{{{input}}} - {产品名称}：{{{product}}} 2. 说话人判断 - 明确每条消息是谁说的：...
"""

import pycorrector
from transformers import pipeline

def process_customer_message(outputList, input_msg, product):
    # 1. 解析聊天历史记录，判断说话人
    speaker_info = []
    for msg in outputList:
        if isinstance(msg, dict):
            # 处理字典格式消息
            sender = msg.get('sender', '').strip()
            content = msg.get('content', str(msg)).strip()
            if sender in ['客户经理', '你']:
                speaker_info.append(('客户经理', content))
            else:
                speaker_info.append(('博主', content))
        elif isinstance(msg, str) and ':' in msg:
            # 处理字符串格式消息 "发送者: 消息内容"
            sender, content = msg.split(':', 1)
            if sender.strip() in ['客户经理', '你']:
                speaker_info.append(('客户经理', content.strip()))
            else:
                speaker_info.append(('博主', content.strip()))
        else:
            # 默认假设未知格式消息为博主（对方）发送
            speaker_info.append(('博主', str(msg).strip()))
    
    # 2. 处理客户消息中的错别字、拼音或方言
    try:
        # 尝试使用pycorrector进行纠错
        corrected_msg, details = pycorrector.correct(input_msg)
    except Exception as e:
        # 纠错失败时使用原始消息
        corrected_msg = input_msg
        details = [f"纠错处理失败: {str(e)}"]
    
    # 3. 结合上下文推断客户真实意图
    try:
        # 准备上下文信息
        context = "\n".join([f"{speaker}: {content}" for speaker, content in speaker_info])
        
        # 使用中文文本生成模型来推断意图
        generator = pipeline("text-generation", model="uer/gpt2-chinese-cluecorpussmall")
        
        # 构建提示文本
        prompt = f"产品: {product}\n上下文: {context}\n用户消息: {corrected_msg}\n客户的意图是:"
        
        # 生成意图
        result = generator(prompt, max_length=len(prompt) + 50, num_return_sequences=1, pad_token_id=50256)
        intent = result[0]['generated_text'][len(prompt):].strip()
    except Exception as e:
        # 意图识别失败时返回错误信息
        intent = f"意图识别失败: {str(e)}"
    
    return {
        "original_message": input_msg,
        "corrected_message": corrected_msg,
        "correction_details": details,
        "context": context,
        "product": product,
        "intent": intent
    }
