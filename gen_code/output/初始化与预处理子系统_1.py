"""
初始化与预处理子系统 - 自动生成的代码
原始需求: 【前置动作】1. 读取信息 - 聊天历史记录：{{{outputList}}} - 当前客户消息：{{{input}}} - {产品名称}：{{{product}}} 2. 说话人判断 - 明确每条消...
"""

import pycorrector
from transformers import BertTokenizer, BertForSequenceClassification
import torch

def process_chat(outputList, input_msg, product):
    # 读取信息
    chat_history = outputList
    current_message = input_msg
    product_name = product
    
    # 处理聊天历史中的说话人判断
    processed_history = []
    for msg in chat_history:
        if isinstance(msg, str):
            if msg.startswith("客户经理:"):
                sender = "客户经理"
                content = msg[len("客户经理:"):].strip()
            elif msg.startswith("博主:"):
                sender = "博主"
                content = msg[len("博主:"):].strip()
            else:
                sender = "未知"
                content = msg.strip()
            processed_history.append({"sender": sender, "content": content})
        else:
            processed_history.append({"sender": "未知", "content": str(msg)})
    
    # 判断当前消息说话人
    if current_message.startswith("客户经理:"):
        current_sender = "客户经理"
        current_content = current_message[len("客户经理:"):].strip()
    elif current_message.startswith("博主:"):
        current_sender = "博主"
        current_content = current_message[len("博主:"):].strip()
    else:
        current_sender = "未知"
        current_content = current_message.strip()
    
    # 错别字与拼音纠错
    corrected_content, _ = pycorrector.correct(current_content)
    
    # 意图识别 (BERT模型)
    tokenizer = BertTokenizer.from_pretrained("bert-base-chinese")
    model = BertForSequenceClassification.from_pretrained("bert-base-chinese", num_labels=3)
    inputs = tokenizer(corrected_content, return_tensors="pt", padding=True, truncation=True, max_length=128)
    
    with torch.no_grad():
        outputs = model(**inputs)
    intent_id = torch.argmax(outputs.logits, dim=1).item()
    intent_map = {0: "咨询", 1: "投诉", 2: "其他"}
    intent = intent_map.get(intent_id, "未知")
    
    return {
        "product_name": product_name,
        "chat_history": processed_history,
        "current_message": {
            "sender": current_sender,
            "original_content": current_content,
            "corrected_content": corrected_content,
            "intent": intent
        }
    }
