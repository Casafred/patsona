"""置信度计算模块 - 融合规则匹配度和LLM置信度"""


class ConfidenceCalculator:
    """置信度计算器

    融合策略：
    - 规则匹配度权重: 0.2
    - LLM 置信度权重: 0.8

    规则匹配度反映关键词/正则的客观命中情况，
    LLM 置信度反映语义理解的判断结果，
    两者加权融合得到最终置信度。
    """

    # 权重配置
    RULE_WEIGHT = 0.2
    LLM_WEIGHT = 0.8

    def calculate(self, rule_score: float, llm_confidence: float) -> float:
        """计算综合置信度

        Args:
            rule_score: 规则匹配度得分 (0.0 ~ 1.0)
            llm_confidence: LLM 给出的置信度 (0.0 ~ 1.0)

        Returns:
            综合置信度 (0.0 ~ 1.0)
        """
        # 输入范围校验
        rule_score = max(0.0, min(1.0, rule_score))
        llm_confidence = max(0.0, min(1.0, llm_confidence))

        combined = rule_score * self.RULE_WEIGHT + llm_confidence * self.LLM_WEIGHT
        return round(combined, 4)

    def needs_review(self, confidence: float, threshold: float = 0.6) -> bool:
        """判断是否需要人工审核

        Args:
            confidence: 综合置信度
            threshold: 审核阈值

        Returns:
            True 表示需要人工审核
        """
        return confidence < threshold
