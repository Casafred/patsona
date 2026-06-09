"""Layer1 粗分类 - 纯规则匹配，关键词命中排除不相关分支，不调用LLM"""

from patsona.classifier.types import CandidateBranch
from patsona.extractor.rule_extractor import RuleExtractor, TechBranchRule
from patsona.preprocessor.parser import PatentDocument


class Layer1Coarse:
    """Layer1 粗分类器

    核心策略：
    1. 对专利文本进行关键词匹配
    2. 对专利文本进行正则模式匹配
    3. 排除命中排除关键词的分支
    4. 按匹配度排序，返回 Top-K 候选分支

    不调用 LLM，纯规则驱动，速度快。
    """

    # 默认返回的候选数量
    DEFAULT_TOP_K = 5

    def __init__(self, top_k: int = DEFAULT_TOP_K) -> None:
        self.top_k = top_k
        self.extractor = RuleExtractor()

    def filter(
        self,
        patent_doc: PatentDocument,
        all_rules: list[TechBranchRule],
    ) -> list[CandidateBranch]:
        """执行粗分类过滤

        Args:
            patent_doc: 解析后的专利文档
            all_rules: 所有技术分支规则

        Returns:
            按匹配度降序排列的 Top-K 候选分支列表
        """
        # 使用核心文本（摘要+权利要求1）进行匹配
        text = patent_doc.summary_text

        # 如果核心文本为空，退而使用全文
        if not text.strip():
            text = patent_doc.full_text

        # 执行规则匹配
        rule_matches = self.extractor.match_rules(text, all_rules)

        # 转换为候选分支
        candidates: list[CandidateBranch] = []
        for match in rule_matches:
            # 查找对应的规则以获取 parent_id
            parent_id = ""
            for rule in all_rules:
                if rule.branch_id == match.branch_id:
                    parent_id = rule.parent_id
                    break

            candidates.append(
                CandidateBranch(
                    branch_id=match.branch_id,
                    branch_name=match.branch_name,
                    score=match.score,
                    matched_keywords=match.matched_keywords,
                    parent_id=parent_id,
                )
            )

        # 返回 Top-K
        return candidates[: self.top_k]
