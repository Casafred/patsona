"""分类结果数据类型定义 - 独立模块，避免循环导入"""

from dataclasses import dataclass, field


@dataclass
class CandidateBranch:
    """Layer1 输出的候选分支"""

    # 分支ID
    branch_id: str
    # 分支名称
    branch_name: str
    # 规则匹配得分
    score: float
    # 命中的关键词
    matched_keywords: list[str] = field(default_factory=list)
    # 父节点ID
    parent_id: str = ""


@dataclass
class ScoredBranch:
    """Layer2 输出的带置信度分支"""

    # 分支ID
    branch_id: str
    # 分支名称
    branch_name: str
    # LLM 给出的置信度 (0.0 ~ 1.0)
    confidence: float
    # LLM 给出的判定依据
    reasoning: str = ""
    # 匹配的关键特征
    key_features: list[str] = field(default_factory=list)


@dataclass
class FinalResult:
    """Layer3 输出的最终分类结果"""

    # 最终分支ID
    branch_id: str
    # 最终分支名称
    branch_name: str
    # 置信度
    confidence: float
    # 判定依据
    reasoning: str
    # 关键区分特征
    distinguishing_features: list[str] = field(default_factory=list)
    # 参考的样本专利ID
    referenced_samples: list[str] = field(default_factory=list)


@dataclass
class PathStep:
    """分类路径上的一个节点"""

    # 分支ID
    branch_id: str
    # 分支名称
    branch_name: str
    # 层级深度（1=根，2=二级...）
    level: int
    # 该层使用的分类方法: "rule" / "llm" / "rule+llm"
    method: str = ""
    # 该层置信度
    confidence: float = 0.0
    # 该层判定依据
    reasoning: str = ""


@dataclass
class LayerResult:
    """单层分类结果"""

    layer_name: str
    # 该层输出的候选分支ID列表
    candidate_ids: list[str] = field(default_factory=list)
    # 该层输出的候选分支名称列表
    candidate_names: list[str] = field(default_factory=list)
    # 该层置信度
    confidence: float = 0.0
    # 该层附加信息
    detail: str = ""


@dataclass
class ClassificationResult:
    """最终分类结果"""

    # 最终分支ID（叶子节点）
    branch_id: str = ""
    # 最终分支名称（叶子节点）
    branch_name: str = ""
    # 完整分类路径：从根到叶子的每一级
    path: list[PathStep] = field(default_factory=list)
    # 完整路径描述：如 "小电动螺丝批-按压启动 > 单一按压启动 > 机械开关触发"
    path_display: str = ""
    # 综合置信度
    confidence: float = 0.0
    # 判定依据
    reasoning: str = ""
    # 各层分类结果
    layer_results: list[LayerResult] = field(default_factory=list)
    # 是否需要人工审核
    needs_review: bool = False
