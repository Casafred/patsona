"""Layer2 中分类 - 调用LLM，传入专利摘要+权利要求1+候选分支判定标准，返回Top-2候选+置信度"""

from typing import Optional

from patsona.classifier.types import CandidateBranch, ScoredBranch
from patsona.llm.client import LLMClient
from patsona.llm.parser import LLMOutputParser
from patsona.llm.prompts import PromptManager
from patsona.preprocessor.parser import PatentDocument


class Layer2Medium:
    """Layer2 中分类器

    核心策略：
    1. 将专利摘要 + 权利要求1 + 各候选分支的判定标准发给LLM
    2. LLM 对每个候选分支给出置信度评分
    3. 返回 Top-2 候选 + 置信度

    Args:
        model_override: 可选的模型覆盖
    """

    # 返回的候选数量
    TOP_K = 2

    def __init__(self, model_override: Optional[str] = None) -> None:
        self.llm_client = LLMClient(model_override=model_override)
        self.prompt_manager = PromptManager()
        self.output_parser = LLMOutputParser()

    def classify(
        self,
        patent_doc: PatentDocument,
        candidates: list[CandidateBranch],
    ) -> list[ScoredBranch]:
        """执行中分类

        Args:
            patent_doc: 解析后的专利文档
            candidates: Layer1 输出的候选分支列表

        Returns:
            按置信度降序排列的 Top-2 候选分支
        """
        if not candidates:
            return []

        # 构建 Prompt
        messages = self.prompt_manager.get_layer2_prompt(patent_doc, candidates)

        # 调用 LLM（要求 JSON 输出）
        try:
            response_text = self.llm_client.chat_json(messages)
            parsed = self.output_parser.parse_json(response_text)
        except Exception as e:
            # LLM 调用失败，打印详细错误
            print(f"[DEBUG] Layer2 LLM调用失败: {type(e).__name__}: {e}")
            return self._fallback_from_candidates(candidates)

        # 解析 LLM 输出
        scored_branches = self._parse_llm_output(parsed, candidates)

        # 返回 Top-K
        scored_branches.sort(key=lambda b: b.confidence, reverse=True)
        return scored_branches[: self.TOP_K]

    def _parse_llm_output(
        self,
        parsed: dict,
        candidates: list[CandidateBranch],
    ) -> list[ScoredBranch]:
        """解析 LLM 返回的 JSON 结构"""
        scored: list[ScoredBranch] = []

        classifications = parsed.get("classifications", [])
        if not classifications:
            if "branch_id" in parsed:
                classifications = [parsed]

        for item in classifications:
            branch_id = item.get("branch_id", "")
            branch_name = item.get("branch_name", "")
            confidence = float(item.get("confidence", 0.0))
            reasoning = item.get("reasoning", "")
            key_features = item.get("key_features", [])

            confidence = max(0.0, min(1.0, confidence))

            scored.append(
                ScoredBranch(
                    branch_id=branch_id,
                    branch_name=branch_name,
                    confidence=confidence,
                    reasoning=reasoning,
                    key_features=key_features,
                )
            )

        if not scored:
            return self._fallback_from_candidates(candidates)

        return scored

    def _fallback_from_candidates(
        self, candidates: list[CandidateBranch]
    ) -> list[ScoredBranch]:
        """LLM调用失败时的回退策略：将规则匹配得分转为置信度"""
        scored: list[ScoredBranch] = []
        for c in candidates[: self.TOP_K]:
            scored.append(
                ScoredBranch(
                    branch_id=c.branch_id,
                    branch_name=c.branch_name,
                    confidence=c.score * 0.5,
                    reasoning="LLM调用失败，基于规则匹配得分回退",
                )
            )
        return scored
