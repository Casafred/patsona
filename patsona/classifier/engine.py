"""递进式逐层分类引擎 - 从根到叶子逐层细分，返回完整分类路径

分类流程：
1. 找到所有一级分支（根节点）
2. 在一级分支中筛选 → 确定1级分类
3. 在该1级分支的子分支中筛选 → 确定2级分类
4. 重复直到叶子节点（无子分支的节点）
5. 返回完整路径: A > A.B > A.B.C

每一层的筛选策略：
- 优先用规则关键词匹配（零成本）
- 规则匹配不足时调用LLM判定
"""

import logging
from typing import Optional

from patsona.classifier.layer2_medium import Layer2Medium
from patsona.classifier.layer3_fine import Layer3Fine
from patsona.classifier.types import (
    CandidateBranch,
    ClassificationResult,
    LayerResult,
    PathStep,
    ScoredBranch,
)
from patsona.config import settings
from patsona.extractor.rule_extractor import RuleExtractor, TechBranchRule
from patsona.preprocessor.parser import PatentDocument

logger = logging.getLogger(__name__)


def _build_tree_index(rules: list[TechBranchRule]) -> dict:
    """构建规则树索引

    Returns:
        {
            "by_id": {branch_id: TechBranchRule},
            "children": {parent_id: [TechBranchRule, ...]},
            "roots": [TechBranchRule, ...],  # 一级分支
        }
    """
    by_id: dict[str, TechBranchRule] = {}
    children: dict[str, list[TechBranchRule]] = {}
    roots: list[TechBranchRule] = []

    for rule in rules:
        by_id[rule.branch_id] = rule
        pid = rule.parent_id
        if pid:
            children.setdefault(pid, []).append(rule)
        else:
            roots.append(rule)

    return {"by_id": by_id, "children": children, "roots": roots}


def _is_leaf(rule: TechBranchRule, tree: dict) -> bool:
    """判断是否为叶子节点（无子分支）"""
    return rule.branch_id not in tree["children"] or len(tree["children"][rule.branch_id]) == 0


class ClassificationEngine:
    """递进式逐层分类引擎

    从根节点开始，逐层向下细分，直到叶子节点。
    每一层：先用规则匹配筛选，规则不足时调用LLM判定。

    Args:
        model_override: 可选的模型覆盖
    """

    def __init__(self, model_override: Optional[str] = None) -> None:
        self.model_override = model_override
        self.extractor = RuleExtractor()
        self.layer2 = Layer2Medium(model_override=model_override)
        self.layer3 = Layer3Fine(model_override=model_override)

    def classify(
        self,
        patent_doc: PatentDocument,
        rules: list[TechBranchRule],
    ) -> ClassificationResult:
        """执行逐层递进分类

        Args:
            patent_doc: 解析后的专利文档
            rules: 技术分支规则列表（扁平）

        Returns:
            ClassificationResult 包含完整分类路径
        """
        result = ClassificationResult()
        tree = _build_tree_index(rules)

        # 如果没有根节点，尝试把所有规则当作根
        roots = tree["roots"]
        if not roots:
            # 所有规则都没有parent_id，直接作为根
            roots = rules

        if not roots:
            result.branch_id = "UNCATEGORIZED"
            result.branch_name = "未分类"
            result.confidence = 0.0
            result.reasoning = "没有可用的分类规则"
            result.needs_review = True
            return result

        # 从根节点开始逐层分类
        current_candidates = roots
        level = 1

        while current_candidates:
            # 如果当前层只有一个候选且没有关键词/规则，自动展开到子分支
            # 这种情况通常是"容器节点"（如根节点），只起分组作用
            if len(current_candidates) == 1:
                only = current_candidates[0]
                has_rules = only.keywords or only.patterns or only.criteria
                has_children = not _is_leaf(only, tree)
                if not has_rules and has_children:
                    # 自动展开：把这个容器节点加入路径，然后直接进入子分支
                    result.path.append(PathStep(
                        branch_id=only.branch_id,
                        branch_name=only.branch_name,
                        level=level,
                        method="auto",
                        confidence=1.0,
                        reasoning="容器节点，自动展开到子分支",
                    ))
                    current_candidates = tree["children"].get(only.branch_id, [])
                    level += 1
                    continue

            # 在当前层级的候选中筛选
            selected = self._classify_at_level(
                patent_doc, current_candidates, tree, level
            )

            if not selected:
                # 当前层无法细分，停留在上一级
                break

            # 记录路径
            result.path.append(PathStep(
                branch_id=selected.branch_id,
                branch_name=selected.branch_name,
                level=level,
                method=selected.method,
                confidence=selected.confidence,
                reasoning=selected.reasoning,
            ))

            # 检查是否为叶子节点
            if _is_leaf(selected.rule, tree):
                break

            # 继续在子分支中细分
            child_rules = tree["children"].get(selected.branch_id, [])
            if not child_rules:
                break

            current_candidates = child_rules
            level += 1

        # 构建最终结果
        if result.path:
            leaf = result.path[-1]
            result.branch_id = leaf.branch_id
            result.branch_name = leaf.branch_name
            result.path_display = " > ".join(
                f"{p.branch_name}" for p in result.path
            )
            # 综合置信度：取路径上最低置信度
            result.confidence = min(p.confidence for p in result.path) if result.path else 0.0
            result.reasoning = "; ".join(
                f"L{p.level}({p.branch_name}): {p.reasoning}" for p in result.path if p.reasoning
            )
            result.needs_review = result.confidence < settings.confidence_threshold
        else:
            result.branch_id = "UNCATEGORIZED"
            result.branch_name = "未分类"
            result.confidence = 0.0
            result.reasoning = "无法匹配任何分类分支"
            result.needs_review = True

        return result

    def _classify_at_level(
        self,
        patent_doc: PatentDocument,
        candidates: list[TechBranchRule],
        tree: dict,
        level: int,
    ) -> Optional["_LevelResult"]:
        """在某一层级进行分类

        策略：
        1. 规则关键词匹配，缩小候选范围
        2. 始终调用LLM做最终判定（规则只做预筛，LLM做决策）
        3. 唯一候选时跳过LLM

        Args:
            patent_doc: 专利文档
            candidates: 当前层级的候选规则列表
            tree: 规则树索引
            level: 当前层级

        Returns:
            _LevelResult 或 None
        """
        text = patent_doc.summary_text
        if not text.strip():
            text = patent_doc.full_text

        # 唯一候选，无需LLM
        if len(candidates) == 1:
            rule = candidates[0]
            return _LevelResult(
                branch_id=rule.branch_id,
                branch_name=rule.branch_name,
                confidence=0.3,
                method="rule",
                reasoning="唯一候选分支",
                rule=rule,
            )

        # Step 1: 规则匹配，缩小候选范围
        rule_matches = self.extractor.match_rules(text, candidates)

        # Step 2: 构建LLM候选列表
        # 优先使用规则匹配结果（有得分排序），无匹配则用全部候选
        if rule_matches:
            candidate_branches = []
            for m in rule_matches[:5]:
                rule = tree["by_id"].get(m.branch_id)
                candidate_branches.append(CandidateBranch(
                    branch_id=m.branch_id,
                    branch_name=m.branch_name,
                    score=m.score,
                    matched_keywords=m.matched_keywords,
                    parent_id=rule.parent_id if rule else "",
                ))
        else:
            candidate_branches = []
            for rule in candidates:
                candidate_branches.append(CandidateBranch(
                    branch_id=rule.branch_id,
                    branch_name=rule.branch_name,
                    score=0.0,
                    parent_id=rule.parent_id,
                ))

        # Step 3: 调用LLM判定
        return self._llm_classify(patent_doc, candidate_branches, tree, level)

    def _llm_classify(
        self,
        patent_doc: PatentDocument,
        candidates: list[CandidateBranch],
        tree: dict,
        level: int,
    ) -> Optional["_LevelResult"]:
        """调用LLM在当前层级进行分类判定"""
        try:
            # Layer2: LLM + 判定标准
            scored = self.layer2.classify(patent_doc, candidates)

            if not scored:
                return None

            best = scored[0]
            threshold = settings.confidence_threshold

            if best.confidence >= threshold:
                return _LevelResult(
                    branch_id=best.branch_id,
                    branch_name=best.branch_name,
                    confidence=best.confidence,
                    method="llm",
                    reasoning=best.reasoning,
                    rule=tree["by_id"].get(best.branch_id),
                )

            # Layer3: 置信度不足，细分类
            final = self.layer3.classify(patent_doc, scored)
            return _LevelResult(
                branch_id=final.branch_id,
                branch_name=final.branch_name,
                confidence=final.confidence,
                method="llm",
                reasoning=final.reasoning,
                rule=tree["by_id"].get(final.branch_id),
            )

        except Exception as e:
            logger.warning(f"Level{level} LLM分类失败: {e}")
            # LLM失败，回退到规则匹配得分最高的
            if candidates:
                best = candidates[0]
                return _LevelResult(
                    branch_id=best.branch_id,
                    branch_name=best.branch_name,
                    confidence=best.score * 0.5,
                    method="rule",
                    reasoning=f"LLM调用失败，基于规则匹配回退: {e}",
                    rule=tree["by_id"].get(best.branch_id),
                )
            return None


class _LevelResult:
    """单层分类结果（内部使用）"""

    def __init__(
        self,
        branch_id: str,
        branch_name: str,
        confidence: float,
        method: str,
        reasoning: str,
        rule: Optional[TechBranchRule] = None,
    ):
        self.branch_id = branch_id
        self.branch_name = branch_name
        self.confidence = confidence
        self.method = method
        self.reasoning = reasoning
        self.rule = rule
