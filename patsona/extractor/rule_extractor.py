"""规则特征提取器 - 基于关键词和正则匹配进行快速过滤，不调用LLM"""

import re
from dataclasses import dataclass, field


@dataclass
class RuleMatch:
    """单条规则的匹配结果"""

    # 规则/分支ID
    branch_id: str
    # 分支名称
    branch_name: str = ""
    # 匹配到的关键词列表
    matched_keywords: list[str] = field(default_factory=list)
    # 匹配到的正则模式列表
    matched_patterns: list[str] = field(default_factory=list)
    # 匹配度得分 (0.0 ~ 1.0)
    score: float = 0.0


@dataclass
class TechBranchRule:
    """技术分支的规则定义（与 YAML 规则文件结构对应）"""

    # 分支ID
    branch_id: str
    # 分支名称
    branch_name: str
    # 父节点ID（用于层级关系）
    parent_id: str = ""
    # 关键词列表
    keywords: list[str] = field(default_factory=list)
    # 正则模式列表
    patterns: list[str] = field(default_factory=list)
    # 排除关键词（命中则排除该分支）
    exclude_keywords: list[str] = field(default_factory=list)
    # 判定标准描述（供LLM使用）
    criteria: str = ""
    # 详细判定标准（Layer3使用）
    detailed_criteria: str = ""


class RuleExtractor:
    """规则特征提取器

    核心职责：
    1. 对专利文本进行关键词匹配
    2. 对专利文本进行正则模式匹配
    3. 计算文本与各规则的匹配度得分
    4. 用于 Layer1 粗筛，快速排除不相关分支
    """

    def extract_keywords(self, text: str, rule: TechBranchRule) -> list[str]:
        """提取文本中命中的关键词

        Args:
            text: 专利文本
            rule: 技术分支规则

        Returns:
            命中的关键词列表（去重）
        """
        matched: list[str] = []
        text_lower = text.lower()

        for keyword in rule.keywords:
            # 支持大小写不敏感匹配
            if keyword.lower() in text_lower:
                matched.append(keyword)

        return list(dict.fromkeys(matched))  # 去重并保持顺序

    def match_patterns(self, text: str, rule: TechBranchRule) -> list[str]:
        """对文本进行正则模式匹配

        Args:
            text: 专利文本
            rule: 技术分支规则

        Returns:
            命中的正则模式列表
        """
        matched: list[str] = []

        for pattern in rule.patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    matched.append(pattern)
            except re.error:
                # 正则语法错误，跳过该模式
                continue

        return matched

    def check_exclusions(self, text: str, rule: TechBranchRule) -> bool:
        """检查文本是否命中排除关键词

        Args:
            text: 专利文本
            rule: 技术分支规则

        Returns:
            True 表示应排除该分支
        """
        text_lower = text.lower()
        for keyword in rule.exclude_keywords:
            if keyword.lower() in text_lower:
                return True
        return False

    def match_rules(self, text: str, rules: list[TechBranchRule]) -> list[RuleMatch]:
        """对文本进行所有规则的匹配，返回匹配结果

        Args:
            text: 专利文本
            rules: 技术分支规则列表

        Returns:
            按匹配度降序排列的匹配结果列表
        """
        matches: list[RuleMatch] = []

        for rule in rules:
            # 先检查排除关键词
            if self.check_exclusions(text, rule):
                continue

            # 关键词匹配
            matched_keywords = self.extract_keywords(text, rule)

            # 正则匹配
            matched_patterns = self.match_patterns(text, rule)

            # 计算匹配度得分
            score = self._calculate_score(
                matched_keywords, matched_patterns, rule
            )

            if score > 0:
                matches.append(
                    RuleMatch(
                        branch_id=rule.branch_id,
                        branch_name=rule.branch_name,
                        matched_keywords=matched_keywords,
                        matched_patterns=matched_patterns,
                        score=score,
                    )
                )

        # 按得分降序排列
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    def _calculate_score(
        self,
        matched_keywords: list[str],
        matched_patterns: list[str],
        rule: TechBranchRule,
    ) -> float:
        """计算规则匹配度得分

        得分策略：
        - 关键词命中率 = 命中关键词数 / 总关键词数
        - 正则命中率 = 命中正则数 / 总正则数
        - 综合得分 = 关键词命中率 * 0.6 + 正则命中率 * 0.4
        - 如果没有定义正则，则纯靠关键词得分

        Args:
            matched_keywords: 命中的关键词
            matched_patterns: 命中的正则模式
            rule: 规则定义

        Returns:
            匹配度得分 (0.0 ~ 1.0)
        """
        if not rule.keywords and not rule.patterns:
            return 0.0

        keyword_score = 0.0
        pattern_score = 0.0

        if rule.keywords:
            keyword_score = len(matched_keywords) / len(rule.keywords)

        if rule.patterns:
            pattern_score = len(matched_patterns) / len(rule.patterns)

        # 根据是否有正则模式调整权重
        if rule.patterns:
            total_score = keyword_score * 0.6 + pattern_score * 0.4
        else:
            total_score = keyword_score

        return min(total_score, 1.0)
