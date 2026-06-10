"""独立权利要求分析引擎

流程：
1. 解析权利要求文本，按编号拆分（代码层，仅做机械拆分）
2. 将全部权利要求交给 LLM，由 LLM 识别独权/从权并深度分析
3. 返回结构化分析结果
"""

import logging
import re
from typing import Optional

from patsona.analyzer.types import (
    ClaimAnalysisResult,
    ClaimComparison,
    ClaimDifference,
    DependentClaimInfo,
    IndependentClaim,
    OutlierClaim,
)
from patsona.llm.client import LLMClient
from patsona.llm.parser import LLMOutputParser
from patsona.llm.prompts import PromptManager

logger = logging.getLogger(__name__)


def parse_claims_text(claims_text: str) -> list[dict]:
    """将权利要求文本按编号拆分为列表

    仅做机械拆分，不判断独权/从权。
    独权/从权的识别交给 LLM 处理。

    支持格式：
    - "1. 一种..." / "1．一种..." / "1、一种..."
    - "权利要求1：一种..."

    Args:
        claims_text: 权利要求书全文

    Returns:
        [{"claim_number": int, "text": str}, ...]
    """
    if not claims_text or not claims_text.strip():
        return []

    # 标准化换行
    text = claims_text.replace("\r\n", "\n").replace("\r", "\n")

    # 按权利要求编号拆分
    # 匹配行首的编号：1. 1． 1、 1: 1：
    parts = re.split(r"(?:^|\n)\s*(\d+)\s*[.．、:：]\s*", text)

    claims: list[dict] = []

    if len(parts) >= 3:
        # parts[0] 是编号前的文本（可能为空）
        # parts[1], parts[2] 是第一组的编号和内容
        # parts[3], parts[4] 是第二组...
        i = 1
        while i + 1 < len(parts):
            try:
                claim_num = int(parts[i].strip())
                claim_text = parts[i + 1].strip()
                if claim_text:
                    claims.append({
                        "claim_number": claim_num,
                        "text": claim_text,
                    })
            except ValueError:
                pass
            i += 2

    # 如果上述拆分没有结果，尝试按行拆分
    if not claims:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            match = re.match(r"(\d+)\s*[.．、:：]\s*(.+)", line)
            if match:
                try:
                    claim_num = int(match.group(1))
                    claim_text = match.group(2).strip()
                    claims.append({
                        "claim_number": claim_num,
                        "text": claim_text,
                    })
                except ValueError:
                    continue

    return claims


class ClaimAnalyzer:
    """独立权利要求分析引擎

    1. 代码层：按编号拆分权利要求文本（仅做机械拆分）
    2. LLM层：识别独权/从权 + 深度分析独权 + 对比 + 异常标识
    """

    def __init__(self, model_override: Optional[str] = None) -> None:
        self.model_override = model_override
        self.llm_client = LLMClient(model_override=model_override)
        self.prompt_manager = PromptManager()
        self.output_parser = LLMOutputParser()

    def analyze(self, claims_text: str) -> ClaimAnalysisResult:
        """执行独立权利要求分析

        Args:
            claims_text: 权利要求书全文

        Returns:
            ClaimAnalysisResult 结构化分析结果
        """
        # Step 1: 按编号拆分权利要求
        claims = parse_claims_text(claims_text)
        if not claims:
            return ClaimAnalysisResult(
                total_claims=0,
                summary="无法解析权利要求文本，请检查输入格式",
            )

        # Step 2: 调用 LLM 分析全部权利要求
        try:
            llm_result = self._llm_analyze(claims)
        except Exception as e:
            logger.warning(f"LLM分析失败: {e}")
            return ClaimAnalysisResult(
                total_claims=len(claims),
                summary=f"LLM分析失败: {e}",
            )

        # Step 3: 构建结构化结果
        result = self._build_result(llm_result, claims)
        return result

    def _llm_analyze(self, all_claims: list[dict]) -> dict:
        """调用 LLM 分析全部权利要求

        Args:
            all_claims: 全部权利要求列表

        Returns:
            LLM 返回的解析后 JSON 字典
        """
        messages = self.prompt_manager.get_claim_analysis_prompt(all_claims)
        response_text = self.llm_client.chat_json(messages, max_tokens=4000)
        parsed = self.output_parser.parse_json(response_text)
        return parsed

    def _build_result(
        self,
        llm_result: dict,
        all_claims: list[dict],
    ) -> ClaimAnalysisResult:
        """将 LLM 输出合并为结构化结果

        Args:
            llm_result: LLM 返回的 JSON 字典
            all_claims: 原始权利要求列表

        Returns:
            ClaimAnalysisResult
        """
        # 构建原文映射
        text_map = {c["claim_number"]: c["text"] for c in all_claims}

        # 解析 independent_claims
        parsed_independent: list[IndependentClaim] = []
        for item in llm_result.get("independent_claims", []):
            claim_num = int(item.get("claim_number", 0))
            parsed_independent.append(IndependentClaim(
                claim_number=claim_num,
                original_text=text_map.get(claim_num, ""),
                protection_subject=item.get("protection_subject", ""),
                subject_category=item.get("subject_category", ""),
                key_features=item.get("key_features", []),
                technical_problem=item.get("technical_problem", ""),
                protection_scope_summary=item.get("protection_scope_summary", ""),
            ))

        # 按 claim_number 排序
        parsed_independent.sort(key=lambda x: x.claim_number)

        # 解析 dependent_claims
        parsed_dependent: list[DependentClaimInfo] = []
        for item in llm_result.get("dependent_claims", []):
            claim_num = int(item.get("claim_number", 0))
            refs = item.get("references", [])
            if isinstance(refs, list):
                refs = [int(r) for r in refs]
            else:
                refs = [int(refs)]
            parsed_dependent.append(DependentClaimInfo(
                claim_number=claim_num,
                references=refs,
            ))

        parsed_dependent.sort(key=lambda x: x.claim_number)

        # 解析 comparison
        comparison_data = llm_result.get("comparison", {})
        comparison = ClaimComparison(
            common_features=comparison_data.get("common_features", []),
            differences=[
                ClaimDifference(
                    claim_numbers=[int(n) for n in d.get("claim_numbers", [])],
                    difference=d.get("difference", ""),
                )
                for d in comparison_data.get("differences", [])
            ],
            outlier_claims=[
                OutlierClaim(
                    claim_number=int(o.get("claim_number", 0)),
                    divergence_type=o.get("divergence_type", ""),
                    reason=o.get("reason", ""),
                    unique_direction=o.get("unique_direction", ""),
                )
                for o in comparison_data.get("outlier_claims", [])
            ],
        )

        return ClaimAnalysisResult(
            total_claims=len(all_claims),
            independent_claims=parsed_independent,
            dependent_claims=parsed_dependent,
            comparison=comparison,
            summary=llm_result.get("summary", ""),
        )
