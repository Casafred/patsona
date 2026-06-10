"""独立权利要求分析引擎

流程：
1. 解析权利要求文本，按编号拆分
2. 用规则识别独立权利要求（不引用其他权利要求的即为独权）
3. 将独权文本交给 LLM 进行深度分析
4. 返回结构化分析结果
"""

import logging
import re
from typing import Optional

from patsona.analyzer.types import (
    ClaimAnalysisResult,
    ClaimComparison,
    ClaimDifference,
    IndependentClaim,
    OutlierClaim,
)
from patsona.llm.client import LLMClient
from patsona.llm.parser import LLMOutputParser
from patsona.llm.prompts import PromptManager

logger = logging.getLogger(__name__)

# 从权引用模式：匹配"根据权利要求X所述的"、"如权利要求X所述的"、"按照权利要求X"等
DEPENDENT_CLAIM_PATTERNS = [
    r"根据权利要求\s*(\d+)\s*所述",
    r"如权利要求\s*(\d+)\s*所述",
    r"按照权利要求\s*(\d+)\s*所述",
    r"根据权利要求\s*(\d+)\s*[～\-至]\s*(\d+)\s*所述",
    r"如权利要求\s*(\d+)\s*[～\-至]\s*(\d+)\s*所述",
    r"根据权利要求\s*(\d+)[、，,]\s*(?:权利要求\s*)?(\d+)\s*所述",
    r"如权利要求\s*(\d+)[、，,]\s*(?:权利要求\s*)?(\d+)\s*所述",
    r"根据权利?要求\s*(\d+)",
    r"如权利?要求\s*(\d+)",
    # 英文专利
    r"according\s+to\s+claim\s+(\d+)",
    r"as\s+recited\s+in\s+claim\s+(\d+)",
    r"of\s+claim\s+(\d+)",
    r"as\s+set\s+forth\s+in\s+claim\s+(\d+)",
]


def parse_claims_text(claims_text: str) -> list[dict]:
    """将权利要求文本按编号拆分为列表

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


def identify_independent_claims(claims: list[dict]) -> tuple[list[dict], list[int]]:
    """识别独立权利要求和从属权利要求

    规则：如果某条权利要求引用了其他权利要求，则为从权；否则为独权。

    Args:
        claims: parse_claims_text 的输出

    Returns:
        (独立权利要求列表, 从属权利要求编号列表)
    """
    independent: list[dict] = []
    dependent_numbers: list[int] = []

    for claim in claims:
        text = claim["text"]
        is_dependent = False

        for pattern in DEPENDENT_CLAIM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                is_dependent = True
                break

        if is_dependent:
            dependent_numbers.append(claim["claim_number"])
        else:
            independent.append(claim)

    return independent, dependent_numbers


class ClaimAnalyzer:
    """独立权利要求分析引擎

    1. 代码层：解析权利要求文本，识别独权/从权
    2. LLM层：对独权进行深度分析（保护主题、技术特征、对比、异常标识）
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
        # Step 1: 解析权利要求
        claims = parse_claims_text(claims_text)
        if not claims:
            return ClaimAnalysisResult(
                total_claims=0,
                summary="无法解析权利要求文本，请检查输入格式",
            )

        # Step 2: 识别独权/从权
        independent, dependent_numbers = identify_independent_claims(claims)

        if not independent:
            return ClaimAnalysisResult(
                total_claims=len(claims),
                dependent_claim_numbers=dependent_numbers,
                summary="未识别到独立权利要求",
            )

        # Step 3: 调用 LLM 分析独权
        try:
            llm_result = self._llm_analyze(independent)
        except Exception as e:
            logger.warning(f"LLM分析失败: {e}")
            # LLM 失败时，返回基础结果（仅包含代码识别的部分）
            return ClaimAnalysisResult(
                total_claims=len(claims),
                independent_claims=[
                    IndependentClaim(
                        claim_number=c["claim_number"],
                        original_text=c["text"],
                    )
                    for c in independent
                ],
                dependent_claim_numbers=dependent_numbers,
                summary=f"LLM分析失败，仅完成独权/从权识别: {e}",
            )

        # Step 4: 合并结果
        result = self._build_result(llm_result, independent, len(claims), dependent_numbers)
        return result

    def _llm_analyze(self, independent_claims: list[dict]) -> dict:
        """调用 LLM 分析独立权利要求

        Args:
            independent_claims: 独权列表

        Returns:
            LLM 返回的解析后 JSON 字典
        """
        messages = self.prompt_manager.get_claim_analysis_prompt(independent_claims)
        response_text = self.llm_client.chat_json(messages, max_tokens=4000)
        parsed = self.output_parser.parse_json(response_text)
        return parsed

    def _build_result(
        self,
        llm_result: dict,
        independent_claims: list[dict],
        total_claims: int,
        dependent_numbers: list[int],
    ) -> ClaimAnalysisResult:
        """将 LLM 输出合并为结构化结果

        Args:
            llm_result: LLM 返回的 JSON 字典
            independent_claims: 原始独权列表
            total_claims: 权利要求总数
            dependent_numbers: 从权编号列表

        Returns:
            ClaimAnalysisResult
        """
        # 构建独权原文映射
        text_map = {c["claim_number"]: c["text"] for c in independent_claims}

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

        # 如果 LLM 没有返回某些独权，补充基础信息
        parsed_numbers = {ic.claim_number for ic in parsed_independent}
        for c in independent_claims:
            if c["claim_number"] not in parsed_numbers:
                parsed_independent.append(IndependentClaim(
                    claim_number=c["claim_number"],
                    original_text=c["text"],
                ))

        # 按 claim_number 排序
        parsed_independent.sort(key=lambda x: x.claim_number)

        # 解析 comparison
        comparison_data = llm_result.get("comparison", {})
        comparison = ClaimComparison(
            common_features=comparison_data.get("common_features", []),
            differences=[
                ClaimDifference(
                    claim_numbers=d.get("claim_numbers", []),
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
            total_claims=total_claims,
            independent_claims=parsed_independent,
            dependent_claim_numbers=sorted(dependent_numbers),
            comparison=comparison,
            summary=llm_result.get("summary", ""),
        )
