"""
异常处理子系统 - 自动生成的代码
原始需求: 【前置动作】3. 纠错与意图识别 - 识别客户消息中的错别字、拼音或方言表达，并结合上下文推断真实意图。【全局约束】-单次确认原则：同一问题只确认一次，得到答案后直接承接。...
"""

from pycorrector import correct
from pypinyin import lazy_pinyin
from transformers import BertTokenizer, BertForSequenceClassification
import torch
from typing import Dict, List, Optional

class IntentRecognizer:
    def __init__(self, dialect_dict_path: Optional[str] = None):
        self.confirmation_state: Dict[str, bool] = {}
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
        self.model = BertForSequenceClassification.from_pretrained('bert-base-chinese', num_labels=10)
        self.dialect_dict = self._load_dialect_dict(dialect_dict_path) if dialect_dict_path else {}
    
    def _load_dialect_dict(self, path: str) -> Dict[str, str]:
        dialect_map = {}
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                dialect, standard = line.strip().split('\t')
                dialect_map[dialect] = standard
        return dialect_map
    
    def correct_text(self, text: str) -> str:
        corrected_text, _ = correct(text)
        return corrected_text
    
    def pinyin_to_chinese(self, text: str) -> str:
        # 实际应用中需替换为专业拼音转汉字逻辑
        pinyin_list = lazy_pinyin(text)
        return ''.join(pinyin_list)  # 简化实现
    
    def process_dialect(self, text: str) -> str:
        for dialect, standard in self.dialect_dict.items():
            text = text.replace(dialect, standard)
        return text
    
    def recognize_intent(self, text: str, context: List[str]) -> str:
        full_text = " ".join(context + [text])
        inputs = self.tokenizer(full_text, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        predicted_class_id = outputs.logits.argmax().item()
        intent_map = {i: f"intent_{i}" for i in range(10)}  # 实际应用需替换为真实意图映射
        return intent_map[predicted_class_id]
    
    def _check_confirmation_status(self, question_id: str) -> bool:
        if question_id not in self.confirmation_state:
            self.confirmation_state[question_id] = False
            return True
        return not self.confirmation_state[question_id]
    
    def update_confirmation(self, question_id: str) -> None:
        self.confirmation_state[question_id] = True
    
    def process_message(self, message: str, context: List[str], question_id: str) -> Dict[str, str]:
        # 文本预处理流程
        corrected = self.correct_text(message)
        pinyin_processed = self.pinyin_to_chinese(corrected)
        dialect_processed = self.process_dialect(pinyin_processed)
        
        # 意图识别
        intent = self.recognize_intent(dialect_processed, context)
        
        # 确认状态管理
        need_confirm = self._check_confirmation_status(question_id)
        if need_confirm:
            self.update_confirmation(question_id)
        
        return {
            "original_message": message,
            "processed_message": dialect_processed,
            "intent": intent,
            "need_confirm": need_confirm
        }
