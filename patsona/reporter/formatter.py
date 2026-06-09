"""结果格式化 - 将分类结果格式化为可读文本"""

from patsona.classifier.types import ClassificationResult


def format_single(result: ClassificationResult) -> str:
    """格式化单条分类结果

    Args:
        result: 分类结果

    Returns:
        格式化的文本，适合终端输出
    """
    lines: list[str] = []

    # 分支信息
    lines.append(f"分类结果: {result.branch_name} ({result.branch_id})")
    lines.append(f"置信度: {result.confidence:.2%}")

    # 审核标记
    if result.needs_review:
        lines.append("⚠ 需要人工审核")

    # 判定依据
    if result.reasoning:
        lines.append(f"判定依据: {result.reasoning}")

    # 各层结果
    if result.layer_results:
        lines.append("\n分类过程:")
        for layer in result.layer_results:
            candidates_str = ", ".join(layer.candidate_names) if layer.candidate_names else "无"
            lines.append(f"  {layer.layer_name}: 候选[{candidates_str}] 置信度={layer.confidence:.2f}")
            if layer.detail:
                lines.append(f"    {layer.detail}")

    return "\n".join(lines)


def format_batch(results: list[ClassificationResult]) -> str:
    """格式化批量分类结果（表格形式）

    Args:
        results: 分类结果列表

    Returns:
        格式化的表格文本
    """
    if not results:
        return "无分类结果"

    lines: list[str] = []

    # 表头
    header = f"{'分支ID':<15} {'分支名称':<20} {'置信度':<10} {'审核':<6}"
    lines.append(header)
    lines.append("-" * len(header))

    # 数据行
    for r in results:
        review_mark = "⚠" if r.needs_review else "✓"
        lines.append(
            f"{r.branch_id:<15} {r.branch_name:<20} {r.confidence:<10.2%} {review_mark:<6}"
        )

    # 汇总
    total = len(results)
    review_count = sum(1 for r in results if r.needs_review)
    avg_confidence = sum(r.confidence for r in results) / total if total else 0

    lines.append("")
    lines.append(f"总计: {total} 条 | 平均置信度: {avg_confidence:.2%} | 待审核: {review_count}")

    return "\n".join(lines)


def format_markdown(results: list[ClassificationResult]) -> str:
    """格式化为 Markdown 输出

    Args:
        results: 分类结果列表

    Returns:
        Markdown 格式的文本
    """
    lines: list[str] = []

    lines.append("# 专利分类结果")
    lines.append("")

    if not results:
        lines.append("无分类结果")
        return "\n".join(lines)

    # 汇总表
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 分支ID | 分支名称 | 置信度 | 需审核 |")
    lines.append("|--------|----------|--------|--------|")

    for r in results:
        review = "是" if r.needs_review else "否"
        lines.append(f"| {r.branch_id} | {r.branch_name} | {r.confidence:.2%} | {review} |")

    lines.append("")

    # 详细结果
    lines.append("## 详细结果")
    lines.append("")

    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r.branch_name} ({r.branch_id})")
        lines.append(f"- **置信度**: {r.confidence:.2%}")
        lines.append(f"- **需审核**: {'是' if r.needs_review else '否'}")

        if r.reasoning:
            lines.append(f"- **判定依据**: {r.reasoning}")

        if r.layer_results:
            lines.append("- **分类过程**:")
            for layer in r.layer_results:
                candidates = ", ".join(layer.candidate_names) if layer.candidate_names else "无"
                lines.append(f"  - {layer.layer_name}: 候选[{candidates}] 置信度={layer.confidence:.2f}")

        lines.append("")

    return "\n".join(lines)
