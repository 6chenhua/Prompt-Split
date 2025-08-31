"""
信息收集与管理子系统 - 自动生成的代码
原始需求: 3. 纠错与意图识别 - 识别客户消息中的错别字、拼音或方言表达，并结合上下文推断真实意图。【操作流程】1. 核查信息完整性 - 对{核心信息}进行逐项核查，若存在{缺失或模糊部分}，应明确指出并请客...
"""

import re
from pycorrector import Corrector
from transformers import pipeline

class CustomerMessageProcessor:
    def __init__(self):
        # 初始化核心信息列表
        self.core_info = [
            '品牌名称', '产品名称', '投放总预算', 
            '预算要求及账号规划', '投放形式'
        ]
        self.optional_info = [
            '脚本核心', '达人折扣', '目标人群及粉丝画像', '达人要求'
        ]
        # 状态管理
        self.state = {
            'reminder_count': 0,
            'missing_core_info': [],
            'provided_info': {},
            'customer_attitude': None  # 'unwilling'|'willing'|None
        }
        # 初始化NLP工具
        self.corrector = Corrector()
        self.ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")  # 实际应用需替换为中文NER模型
        self.intent_classifier = pipeline("text-classification", model="bert-base-chinese", num_labels=3)  # 0:正常 1:不愿提供 2:已说明原因

    def correct_text(self, text):
        """文本纠错处理"""
        corrected_text, _ = self.corrector.correct(text)
        return corrected_text

    def extract_info(self, text):
        """提取核心信息"""
        extracted = {}
        # NER提取核心实体
        ner_results = self.ner_pipeline(text)
        for info_type in self.core_info + self.optional_info:
            # 关键词匹配提取
            pattern = re.compile(f"{info_type}[:：]?\\s*([^，,;；。\n]+)")
            match = pattern.search(text)
            if match:
                extracted[info_type] = match.group(1).strip()
        return extracted

    def check_completeness(self, extracted_info):
        """检查信息完整性"""
        missing = [info for info in self.core_info if extracted_info.get(info) is None]
        self.state['missing_core_info'] = missing
        return missing

    def generate_reminder(self):
        """生成催促信息"""
        missing = self.state['missing_core_info']
        if not missing:
            return "信息已完整，感谢您的配合。"
            
        if self.state['reminder_count'] == 0:
            reminder = f"请补充以下必要信息：{', '.join(missing)}"
        else:
            reminder = f"请补充{missing[0]}信息，以便我们继续处理。"
            
        self.state['reminder_count'] += 1
        return reminder

    def handle_unwillingness(self, text):
        """处理不愿提供信息情况"""
        intent_result = self.intent_classifier(text)[0]
        intent_label = intent_result['label']
        
        if intent_label == '1':  # 不愿提供且未说明原因
            self.state['customer_attitude'] = 'unwilling'
            return "了解您的顾虑，能否告知无法提供信息的原因呢？以便我们更好地协助您。"
        elif intent_label == '2':  # 已说明原因
            self.state['customer_attitude'] = 'explained'
            return "感谢您的说明，信息完整性有助于制定更精准的投放方案，希望能得到您的配合。"
        return None

    def process(self, customer_message):
        """处理客户消息主流程"""
        # 1. 文本纠错
        corrected_msg = self.correct_text(customer_message)
        # 2. 意图识别与特殊情况处理
        unwilling_response = self.handle_unwillingness(corrected_msg)
        if unwilling_response:
            return unwilling_response
        # 3. 信息提取与完整性检查
        extracted_info = self.extract_info(corrected_msg)
        self.state['provided_info'].update(extracted_info)
        missing_info = self.check_completeness(self.state['provided_info'])
        # 4. 生成响应
        if missing_info:
            return self.generate_reminder()
        else:
            return "信息已完整，我们将尽快为您制定投放方案。"
