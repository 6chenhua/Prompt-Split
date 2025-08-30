"""
需求处理核心子系统 - 自动生成的代码
原始需求: 【目标】在轻松友好的氛围中快速建立信任，高效收集客户{投放关键信息}，帮助客户明确需求，为后续投放规划和达人筛选做好准备。【核心信息】需要与客户确认的关键内容包括：1. {品牌名称}：确保广告投放归属...
"""

from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import re

class ClientInfoCollector:
    def __init__(self):
        # 核心信息列表（带{}的关键信息项）
        self.core_information = [
            "{品牌名称}", "{产品名称}", "{投放总预算}", "{达人单价}",
            "{投放形式}", "{脚本核心}", "{达人折扣}", "{目标人群及粉丝画像}"
        ]
        
        # 对话状态管理
        self.dialog_state = {
            "collected_info": {},          # 已收集信息
            "confirmed_questions": set(),  # 已确认问题
            "current_step": 0              # 当前对话步骤
        }
        
        # 初始化意图分类器（使用中文预训练模型）
        self.intent_classifier = pipeline(
            "text-classification",
            model="uer/roberta-base-finetuned-dianping-chinese",
            tokenizer=AutoTokenizer.from_pretrained("uer/roberta-base-finetuned-dianping-chinese")
        )

    def error_correction(self, text):
        """中文纠错：处理常见错别字和拼音表达"""
        # 常见错别字映射表
        error_map = {
            "帐号": "账号", "预箅": "预算", "报眚": "报备", 
            "粉絲": "粉丝", "画象": "画像", "创义": "创意",
            "da": "达", "ren": "人", "pinpai": "品牌", "chanpin": "产品"
        }
        for error, correction in error_map.items():
            text = text.replace(error, correction)
        return text

    def intent_recognition(self, text):
        """意图识别：判断用户输入意图类型"""
        result = self.intent_classifier(text)[0]
        return result["label"], result["score"]

    def extract_information(self, text):
        """信息提取：从用户输入中提取核心信息"""
        extracted = {}
        for info in self.core_information:
            # 使用正则表达式匹配信息模式（如"品牌名称：XX"或"品牌名称是XX"）
            pattern = re.compile(f"{re.escape(info)}[:：是]\\s*([^，,。；;\\n]+)")
            match = pattern.search(text)
            if match:
                extracted[info] = match.group(1).strip()
        return extracted

    def get_next_target_sentence(self):
        """获取下一个核心目标句（单次确认原则）"""
        while self.dialog_state["current_step"] < len(self.core_information):
            target = self.core_information[self.dialog_state["current_step"]]
            if target not in self.dialog_state["confirmed_questions"]:
                return f"请确认{target}信息。"
            self.dialog_state["current_step"] += 1
        return "感谢提供信息，将为您制定投放规划。"

    def process_user_input(self, user_input):
        """处理用户输入并更新对话状态"""
        # 1. 纠错处理
        corrected_input = self.error_correction(user_input)
        
        # 2. 意图识别
        intent, confidence = self.intent_recognition(corrected_input)
        
        # 3. 信息提取与状态更新（仅处理高置信度意图）
        if intent == "提供信息" and confidence > 0.7:
            extracted_info = self.extract_information(corrected_input)
            for info, value in extracted_info.items():
                self.dialog_state["collected_info"][info] = value
                self.dialog_state["confirmed_questions"].add(info)
        
        # 4. 生成下一个目标句
        return self.get_next_target_sentence()
