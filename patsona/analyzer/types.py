"""独立权利要求分析 - 数据类型定义"""

from dataclasses import dataclass, field


@dataclass
class IndependentClaim:
    """独立权利要求解析结果"""

    # 权利要求编号
    claim_number: int
    # 权利要求原文
    original_text: str
    # 保护主题（如"一种电动螺丝批"、"一种控制方法"）
    protection_subject: str = ""
    # 主题类别（产品/方法/系统/用途等）
    subject_category: str = ""
    # 关键技术特征列表
    key_features: list[str] = field(default_factory=list)
    # 解决的技术问题
    technical_problem: str = ""
    # 保护范围概述
    protection_scope_summary: str = ""


@dataclass
class DependentClaimInfo:
    """从属权利要求信息"""

    # 权利要求编号
    claim_number: int
    # 引用的权利要求编号
    references: list[int] = field(default_factory=list)


@dataclass
class ClaimDifference:
    """权利要求差异描述"""

    # 对比的独权编号
    claim_numbers: list[int] = field(default_factory=list)
    # 差异描述
    difference: str = ""


@dataclass
class OutlierClaim:
    """异常独权标识 - 与其他独权保护方向差异较大的权利要求"""

    # 权利要求编号
    claim_number: int
    # 差异类型（主题差异/技术路线差异/应用场景差异等）
    divergence_type: str = ""
    # 差异原因说明
    reason: str = ""
    # 该独权独特的保护方向
    unique_direction: str = ""


@dataclass
class ClaimComparison:
    """独权对比分析结果"""

    # 共同点
    common_features: list[str] = field(default_factory=list)
    # 差异点
    differences: list[ClaimDifference] = field(default_factory=list)
    # 异常独权
    outlier_claims: list[OutlierClaim] = field(default_factory=list)


@dataclass
class ClaimAnalysisResult:
    """独立权利要求分析最终结果"""

    # 权利要求总数
    total_claims: int = 0
    # 独立权利要求列表
    independent_claims: list[IndependentClaim] = field(default_factory=list)
    # 从属权利要求信息列表
    dependent_claims: list[DependentClaimInfo] = field(default_factory=list)
    # 对比分析
    comparison: ClaimComparison = field(default_factory=ClaimComparison)
    # 总体分析概述
    summary: str = ""
