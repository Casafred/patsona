"""批量统计 - 分类结果的统计分析"""

from collections import Counter

from patsona.classifier.types import ClassificationResult


class BatchStats:
    """批量分类统计器

    统计内容：
    1. 分类分布（各分支的数量）
    2. 置信度分布（高/中/低）
    3. 待人工审核数量
    4. 各层分类命中率
    """

    # 置信度分级阈值
    HIGH_THRESHOLD = 0.8
    LOW_THRESHOLD = 0.5

    def compute(self, results: list[ClassificationResult]) -> str:
        """计算并格式化统计报告

        Args:
            results: 分类结果列表

        Returns:
            格式化的统计报告文本
        """
        if not results:
            return "无分类结果可供统计"

        lines: list[str] = []
        lines.append("=" * 50)
        lines.append("批量分类统计报告")
        lines.append("=" * 50)

        # 基本统计
        total = len(results)
        lines.append(f"\n总计: {total} 条")

        # 分类分布
        branch_counter = Counter(r.branch_name for r in results)
        lines.append(f"\n分类分布:")
        for branch_name, count in branch_counter.most_common():
            pct = count / total * 100
            lines.append(f"  {branch_name}: {count} ({pct:.1f}%)")

        # 置信度分布
        high = sum(1 for r in results if r.confidence >= self.HIGH_THRESHOLD)
        medium = sum(
            1
            for r in results
            if self.LOW_THRESHOLD <= r.confidence < self.HIGH_THRESHOLD
        )
        low = sum(1 for r in results if r.confidence < self.LOW_THRESHOLD)

        lines.append(f"\n置信度分布:")
        lines.append(f"  高 (≥{self.HIGH_THRESHOLD:.0%}): {high} ({high/total*100:.1f}%)")
        lines.append(f"  中 ({self.LOW_THRESHOLD:.0%}~{self.HIGH_THRESHOLD:.0%}): {medium} ({medium/total*100:.1f}%)")
        lines.append(f"  低 (<{self.LOW_THRESHOLD:.0%}): {low} ({low/total*100:.1f}%)")

        # 平均置信度
        avg_confidence = sum(r.confidence for r in results) / total
        lines.append(f"\n平均置信度: {avg_confidence:.2%}")

        # 待审核数量
        review_count = sum(1 for r in results if r.needs_review)
        lines.append(f"待人工审核: {review_count} ({review_count/total*100:.1f}%)")

        # 各层使用统计
        layer_usage = self._count_layer_usage(results)
        if layer_usage:
            lines.append(f"\n分类层级使用:")
            for layer_name, count in layer_usage.items():
                lines.append(f"  {layer_name}: {count} 次")

        lines.append("=" * 50)

        return "\n".join(lines)

    def _count_layer_usage(self, results: list[ClassificationResult]) -> dict[str, int]:
        """统计各层分类的使用次数"""
        layer_counter: Counter = Counter()

        for r in results:
            for layer in r.layer_results:
                layer_counter[layer.layer_name] += 1

        return dict(layer_counter)

    def get_distribution(self, results: list[ClassificationResult]) -> dict[str, int]:
        """获取分类分布数据

        Args:
            results: 分类结果列表

        Returns:
            分支名称 -> 数量 的映射
        """
        return dict(Counter(r.branch_name for r in results))

    def get_confidence_stats(self, results: list[ClassificationResult]) -> dict:
        """获取置信度统计数据

        Args:
            results: 分类结果列表

        Returns:
            包含 min/max/avg/median 的统计字典
        """
        if not results:
            return {}

        confidences = [r.confidence for r in results]
        sorted_conf = sorted(confidences)

        return {
            "min": sorted_conf[0],
            "max": sorted_conf[-1],
            "avg": sum(confidences) / len(confidences),
            "median": sorted_conf[len(sorted_conf) // 2],
        }
