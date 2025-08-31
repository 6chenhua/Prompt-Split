"""
QA处理子系统 - 自动生成的代码
原始需求: 【全局约束】-如果客户提出问题，先正面回答，再推进需求收集或项目规划。-客户若提出问题，需先回答问题，再引导需求信息收集或预算沟通。-当客户提出直接问题（尤其是“预算范围是多少”“达人单价能做到多少”...
"""

class CustomerServiceDialogueManager:
    def __init__(self):
        # 初始化关键词与模板
        self.direct_question_keywords = {"预算", "单价", "价格", "费用", "多少钱"}
        self.response_templates = {
            "direct_answer": "我们的{topic}范围通常在5000-20000元区间，具体需根据项目复杂度评估。",
            "general_answer": "针对您的问题，我们的回复是：{content}。",
            "direct_guidance": "为了提供更精准的方案，麻烦您补充项目具体需求细节？",
            "general_guidance": "请问您在项目规划方面还有其他需要了解的吗？"
        }

    def _nlp_intent_recognition(self, question):
        """NLP意图识别：提取问题关键词与类型"""
        question_lower = question.lower()
        for keyword in self.direct_question_keywords:
            if keyword in question_lower:
                return "direct_question", keyword
        return "general_question", None

    def _rule_based_classifier(self, intent_result):
        """规则引擎判断问题类型"""
        return intent_result[0], intent_result[1]

    def _generate_answer_section(self, question_type, keyword=None):
        """生成问题答案部分"""
        if question_type == "direct_question":
            return self.response_templates["direct_answer"].format(topic=keyword)
        return self.response_templates["general_answer"].format(content="相关信息已为您记录")

    def _generate_guidance_section(self, question_type):
        """生成需求引导部分"""
        return self.response_templates["direct_guidance"] if question_type == "direct_question" else self.response_templates["general_guidance"]

    def process_query(self, customer_query):
        """主流程：处理客户查询并生成回复"""
        intent, keyword = self._nlp_intent_recognition(customer_query)
        question_type, topic = self._rule_based_classifier((intent, keyword))
        answer_section = self._generate_answer_section(question_type, topic)
        guidance_section = self._generate_guidance_section(question_type)
        return f"{answer_section}\n{guidance_section}"
