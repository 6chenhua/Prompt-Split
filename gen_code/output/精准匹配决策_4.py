"""
精准匹配决策 - 自动生成的代码
原始需求: 用活泼的语气告知客户当已满足模糊匹配达人，询问是否需要精准匹配合适达人。若客户回答不需要或不用精准匹配，则直接进入【第七步】。若客户回答需要或进行精准匹配，则直接进入下一步骤。...
"""

def check_precision_match_need():
    try:
        # 预设活泼语气的提示文本
        prompt = "🎉 恭喜！您已成功模糊匹配到达人啦！需要为您精准匹配更合适的达人吗？"
        print(prompt)
        
        # 获取客户输入
        user_input = input().strip().lower()
        
        # 判断输入内容
        if any(keyword in user_input for keyword in ["不需要", "不用精准匹配"]):
            return ("第七步",)
        elif any(keyword in user_input for keyword in ["需要", "进行精准匹配"]):
            return ("下一步骤",)
        else:
            return (None,)
    except Exception:
        return (None,)
