"""
需求确认与收尾子系统 - 自动生成的代码
原始需求: 【核心信息】可选但有助于精准投放的信息包括：1. {脚本核心}：明确内容创意方向，便于后续创意策划。2. {达人折扣}：如有可优惠报价，可影响达人合作意向。3. {目标人群}及{粉丝画像}：有助于精细...
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DemandInfo:
    # 核心信息字段
    script_core: Optional[str] = None
    talent_discount: Optional[float] = None
    target_audience: Optional[str] = None
    talent_requirements: Optional[str] = None
    special_benefits: Optional[str] = None
    # 额外信息存储
    additional_info: Dict[str, str] = field(default_factory=dict)
    # 需求状态标识
    is_core_complete: bool = False
    is_confirmed: bool = False

    def update_core_info(self, **kwargs) -> None:
        """更新核心信息字段"""
        for key, value in kwargs.items():
            if hasattr(self, key) and key in [
                "script_core", "talent_discount", "target_audience",
                "talent_requirements", "special_benefits"
            ]:
                setattr(self, key, value)
        self.is_core_complete = self._check_core_completeness()

    def _check_core_completeness(self) -> bool:
        """检查核心信息完整性（修复恒为True的错误）"""
        core_fields = [
            self.script_core,
            self.talent_discount,
            self.target_audience,
            self.talent_requirements,
            self.special_benefits
        ]
        return all(field is not None and str(field).strip() != "" for field in core_fields)

    def collect_additional_info(self, **kwargs) -> None:
        """收集额外信息（核心信息完整时调用）"""
        if self.is_core_complete:
            self.additional_info.update(kwargs)

    def confirm_demand(self) -> bool:
        """最终需求确认（仅核心信息完整时可确认）"""
        if self.is_core_complete:
            self.is_confirmed = True
            return True
        return False


class DemandCollector:
    def __init__(self):
        self.demand = DemandInfo()

    def collect_core_info(self, core_data: Dict[str, str]) -> bool:
        """收集核心信息并检查完整性"""
        self.demand.update_core_info(**core_data)
        return self.demand.is_core_complete

    def collect_additional_info(self, additional_data: Dict[str, str]) -> None:
        """触发额外信息收集流程"""
        if self.demand.is_core_complete:
            self.demand.collect_additional_info(**additional_data)

    def final_confirmation(self) -> bool:
        """执行最终需求确认"""
        return self.demand.confirm_demand()
