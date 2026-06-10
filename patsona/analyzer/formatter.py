"""独权分析结果格式化输出"""

from patsona.analyzer.types import ClaimAnalysisResult, IndependentClaim, OutlierClaim


def format_claim_analysis(result: ClaimAnalysisResult) -> str:
    """格式化独权分析结果为终端可读文本

    Args:
        result: 分析结果

    Returns:
        格式化的文本
    """
    lines: list[str] = []

    # 基本统计
    lines.append("=" * 60)
    lines.append("独立权利要求分析报告")
    lines.append("=" * 60)
    lines.append(f"权利要求总数: {result.total_claims}")
    lines.append(f"独立权利要求: {len(result.independent_claims)} 条")
    if result.dependent_claim_numbers:
        lines.append(f"从属权利要求: {len(result.dependent_claim_numbers)} 条 ({', '.join(str(n) for n in result.dependent_claim_numbers)})")
    lines.append("")

    # 逐条独权解析
    lines.append("-" * 60)
    lines.append("一、各独立权利要求解析")
    lines.append("-" * 60)

    for ic in result.independent_claims:
        lines.append("")
        lines.append(f"【权利要求{ic.claim_number}】")
        lines.append(f"  保护主题: {ic.protection_subject}")
        lines.append(f"  主题类别: {ic.subject_category}")

        if ic.key_features:
            lines.append(f"  关键技术特征:")
            for feat in ic.key_features:
                lines.append(f"    - {feat}")

        if ic.technical_problem:
            lines.append(f"  解决的技术问题: {ic.technical_problem}")

        if ic.protection_scope_summary:
            lines.append(f"  保护范围概述: {ic.protection_scope_summary}")

    # 对比分析
    comp = result.comparison
    if comp.common_features or comp.differences or comp.outlier_claims:
        lines.append("")
        lines.append("-" * 60)
        lines.append("二、独权对比分析")
        lines.append("-" * 60)

        if comp.common_features:
            lines.append("")
            lines.append("  共同点:")
            for feat in comp.common_features:
                lines.append(f"    - {feat}")

        if comp.differences:
            lines.append("")
            lines.append("  差异点:")
            for diff in comp.differences:
                nums = ", ".join(str(n) for n in diff.claim_numbers)
                lines.append(f"    - 权利要求{nums}: {diff.difference}")

        if comp.outlier_claims:
            lines.append("")
            lines.append("  ★ 异常独权（保护方向差异较大）:")
            for outlier in comp.outlier_claims:
                lines.append(f"    【权利要求{outlier.claim_number}】")
                lines.append(f"      差异类型: {outlier.divergence_type}")
                lines.append(f"      差异原因: {outlier.reason}")
                lines.append(f"      独特方向: {outlier.unique_direction}")
        else:
            lines.append("")
            lines.append("  异常独权: 无（所有独权保护方向一致）")

    # 总体概述
    if result.summary:
        lines.append("")
        lines.append("-" * 60)
        lines.append("三、总体概述")
        lines.append("-" * 60)
        lines.append(f"  {result.summary}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_claim_analysis_markdown(result: ClaimAnalysisResult) -> str:
    """格式化独权分析结果为 Markdown

    Args:
        result: 分析结果

    Returns:
        Markdown 格式文本
    """
    lines: list[str] = []

    lines.append("# 独立权利要求分析报告")
    lines.append("")

    # 基本统计
    lines.append("## 概览")
    lines.append("")
    lines.append(f"- 权利要求总数: {result.total_claims}")
    lines.append(f"- 独立权利要求: {len(result.independent_claims)} 条")
    if result.dependent_claim_numbers:
        lines.append(f"- 从属权利要求: {len(result.dependent_claim_numbers)} 条 ({', '.join(str(n) for n in result.dependent_claim_numbers)})")
    lines.append("")

    # 逐条独权
    lines.append("## 各独立权利要求解析")
    lines.append("")

    for ic in result.independent_claims:
        lines.append(f"### 权利要求{ic.claim_number}")
        lines.append("")
        lines.append(f"- **保护主题**: {ic.protection_subject}")
        lines.append(f"- **主题类别**: {ic.subject_category}")

        if ic.technical_problem:
            lines.append(f"- **解决的技术问题**: {ic.technical_problem}")

        if ic.protection_scope_summary:
            lines.append(f"- **保护范围概述**: {ic.protection_scope_summary}")

        if ic.key_features:
            lines.append("")
            lines.append("**关键技术特征**:")
            for feat in ic.key_features:
                lines.append(f"  - {feat}")

        lines.append("")

    # 对比分析
    comp = result.comparison
    if comp.common_features or comp.differences or comp.outlier_claims:
        lines.append("## 独权对比分析")
        lines.append("")

        if comp.common_features:
            lines.append("### 共同点")
            lines.append("")
            for feat in comp.common_features:
                lines.append(f"- {feat}")
            lines.append("")

        if comp.differences:
            lines.append("### 差异点")
            lines.append("")
            lines.append("| 涉及权利要求 | 差异描述 |")
            lines.append("|-------------|---------|")
            for diff in comp.differences:
                nums = ", ".join(str(n) for n in diff.claim_numbers)
                lines.append(f"| 权利要求{nums} | {diff.difference} |")
            lines.append("")

        if comp.outlier_claims:
            lines.append("### 异常独权标识")
            lines.append("")
            lines.append("| 权利要求 | 差异类型 | 差异原因 | 独特保护方向 |")
            lines.append("|---------|---------|---------|-------------|")
            for outlier in comp.outlier_claims:
                lines.append(
                    f"| {outlier.claim_number} | {outlier.divergence_type} "
                    f"| {outlier.reason} | {outlier.unique_direction} |"
                )
            lines.append("")
        else:
            lines.append("### 异常独权")
            lines.append("")
            lines.append("无 — 所有独权保护方向一致")
            lines.append("")

    # 总体概述
    if result.summary:
        lines.append("## 总体概述")
        lines.append("")
        lines.append(result.summary)
        lines.append("")

    return "\n".join(lines)
