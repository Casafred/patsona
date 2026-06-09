"""LLM 输出解析器 - 从 LLM 返回的文本中提取结构化数据"""

import json
import re

from patsona.classifier.types import ClassificationResult


class LLMOutputParser:
    """LLM 输出解析器

    处理 LLM 返回文本中的各种格式问题：
    - Markdown 代码块包裹的 JSON
    - JSON 前后的额外文本
    - 格式错误的 JSON 修复
    """

    def parse_json(self, text: str) -> dict:
        """从 LLM 输出文本中提取 JSON 对象

        支持以下格式：
        1. 纯 JSON: {"key": "value"}
        2. Markdown 代码块: ```json\n{...}\n```
        3. JSON 前后有额外文本: 一些说明\n{"key": "value"}\n更多说明

        Args:
            text: LLM 返回的原始文本

        Returns:
            解析后的字典

        Raises:
            ValueError: 无法从文本中提取有效 JSON
        """
        if not text or not text.strip():
            raise ValueError("LLM 输出为空")

        # 策略1: 尝试直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # 策略2: 提取 Markdown 代码块中的 JSON
        code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 策略3: 查找第一个 { 和最后一个 } 之间的内容
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_str = text[first_brace : last_brace + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试修复常见的 JSON 格式问题
                fixed = self._fix_common_json_errors(json_str)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        # 策略4: 查找 [ 开头的 JSON 数组
        first_bracket = text.find("[")
        last_bracket = text.rfind("]")
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            json_str = text[first_bracket : last_bracket + 1]
            try:
                result = json.loads(json_str)
                # 如果是数组，包装为字典
                if isinstance(result, list):
                    return {"classifications": result}
                return result
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从 LLM 输出中提取有效 JSON: {text[:200]}...")

    def parse_classification(self, text: str) -> ClassificationResult:
        """从 LLM 输出解析分类结果

        Args:
            text: LLM 返回的原始文本

        Returns:
            ClassificationResult 分类结果
        """
        parsed = self.parse_json(text)

        return ClassificationResult(
            branch_id=parsed.get("branch_id", ""),
            branch_name=parsed.get("branch_name", ""),
            confidence=float(parsed.get("confidence", 0.0)),
            reasoning=parsed.get("reasoning", ""),
        )

    def _fix_common_json_errors(self, json_str: str) -> str:
        """修复常见的 JSON 格式错误

        处理的问题：
        1. 尾随逗号（trailing comma）
        2. 单引号代替双引号
        3. 注释（// 和 /* */）
        4. 缺少引号的键名
        """
        # 移除单行注释
        json_str = re.sub(r"//.*$", "", json_str, flags=re.MULTILINE)
        # 移除多行注释
        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
        # 移除尾随逗号（}, ] 前的逗号）
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
        # 单引号替换为双引号
        json_str = json_str.replace("'", '"')

        return json_str
