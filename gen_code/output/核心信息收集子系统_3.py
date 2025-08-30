"""
核心信息收集子系统 - 自动生成的代码
原始需求: 【{核心信息}】需要与客户确认的关键内容包括：1. {品牌名称} 2. {产品名称} 3. {投放总预算} 4. {预算要求及账号规划} 5. {投放形式} 6. {内容方向或账号类型} 7. {是否...
"""

from typing import Dict, List, Set, Optional

# 核心信息字段列表
CORE_FIELDS = [
    "品牌名称",
    "产品名称",
    "投放总预算",
    "预算要求及账号规划",
    "投放形式",
    "内容方向或账号类型",
    "是否提供额外信息以便筛选达人"
]

class CustomerInfoManager:
    def __init__(self):
        self.customer_info: Dict[str, Optional[str]] = {field: None for field in CORE_FIELDS}
        self.missing_fields: Set[str] = set(CORE_FIELDS)
        self.confirmed_questions: Set[str] = set()
        self.reminder_count: int = 0
        self.customer_question: Optional[str] = None

    def check_integrity(self) -> Set[str]:
        self.missing_fields = {field for field in CORE_FIELDS if not self.customer_info[field]}
        return self.missing_fields

    def update_customer_info(self, field: str, value: str) -> None:
        if field in CORE_FIELDS and field not in self.confirmed_questions:
            self.customer_info[field] = value
            self.confirmed_questions.add(field)
            if field in self.missing_fields:
                self.missing_fields.remove(field)

    def generate_reminder(self) -> str:
        self.check_integrity()
        if not self.missing_fields:
            return "所有核心信息已收集完整"
            
        self.reminder_count += 1
        if self.reminder_count == 1:
            return f"请补充以下缺失信息：{', '.join(self.missing_fields)}"
        else:
            return f"请补充{next(iter(self.missing_fields))}，感谢配合"

    def handle_unwilling_to_provide(self, field: str, has_reason: bool = False, reason: Optional[str] = None) -> str:
        if not has_reason:
            return f"请问您不愿提供{field}的原因是什么呢？我们会严格保密"
        return (f"{field}对制定投放方案至关重要，完整信息能确保方案有效性。"
                "我们不会修改条款或承诺结果，但会尽力优化方案")

    def handle_customer_question(self, question: str, answer: str) -> str:
        self.customer_question = question
        self.check_integrity()
        guide = "所有信息已完整，将尽快推进方案" if not self.missing_fields else \
                f"另外请补充{next(iter(self.missing_fields))}"
        return f"您的问题：{question}\n回答：{answer}\n{guide}"

    def is_question_confirmed(self, question: str) -> bool:
        return question in self.confirmed_questions
