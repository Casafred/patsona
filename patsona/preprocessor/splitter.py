"""专利文本结构化拆分 - 从全文中提取标题/摘要/权利要求/技术领域等字段"""

import re

from patsona.preprocessor.parser import PatentDocument


class PatentSplitter:
    """将专利全文拆分为结构化字段

    支持两种常见格式：
    1. 带段落标记的正式专利文本（如"【摘要】"、"【权利要求书】"等）
    2. 无标记的纯文本（通过启发式规则尝试拆分）
    """

    # 专利文档段落标记模式（中文专利标准格式）
    SECTION_PATTERNS = {
        "title": [
            r"【发明名称】\s*(.+?)(?=\n|【)",
            r"【标题】\s*(.+?)(?=\n|【)",
            r"发\s*明\s*名\s*称\s*[：:]\s*(.+?)(?=\n)",
        ],
        "abstract": [
            r"【摘要】\s*(.+?)(?=【|$)",
            r"摘\s*要\s*[：:]\s*(.+?)(?=【|$)",
        ],
        "technical_field": [
            r"【技术领域】\s*(.+?)(?=【|$)",
            r"技\s*术\s*领\s*域\s*[：:]\s*(.+?)(?=【|$)",
        ],
        "background": [
            r"【背景技术】\s*(.+?)(?=【|$)",
            r"背\s*景\s*技\s*术\s*[：:]\s*(.+?)(?=【|$)",
        ],
        "claims": [
            r"【权利要求书】\s*(.+?)(?=【|$)",
            r"权\s*利\s*要\s*求\s*书?\s*[：:]\s*(.+?)(?=【|$)",
        ],
    }

    def split_sections(self, text: str) -> PatentDocument:
        """将全文拆分为 PatentDocument 结构

        Args:
            text: 专利全文文本

        Returns:
            解析后的 PatentDocument 对象
        """
        doc = PatentDocument(raw_text=text)

        # 标准化换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 尝试按段落标记提取
        title = self._extract_section(text, "title")
        abstract = self._extract_section(text, "abstract")
        technical_field = self._extract_section(text, "technical_field")
        background = self._extract_section(text, "background")
        claims_text = self._extract_section(text, "claims")

        # 如果标记提取失败，尝试启发式拆分
        if not abstract and not claims_text:
            doc = self._heuristic_split(text)
        else:
            doc.title = title.strip()
            doc.abstract = abstract.strip()
            doc.technical_field = technical_field.strip()
            doc.background = background.strip()
            doc.claims = self._parse_claims(claims_text)

        # 如果没有标题，尝试取第一行
        if not doc.title:
            first_line = text.strip().split("\n")[0].strip()
            if len(first_line) <= 100:
                doc.title = first_line

        return doc

    def _extract_section(self, text: str, section: str) -> str:
        """使用正则模式提取指定段落内容"""
        patterns = self.SECTION_PATTERNS.get(section, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        return ""

    def _parse_claims(self, claims_text: str) -> list[str]:
        """解析权利要求文本为列表

        支持格式：
        - "1. 一种..." / "1．一种..."
        - "权利要求1: 一种..."
        """
        if not claims_text:
            return []

        claims: list[str] = []

        # 按权利要求编号拆分
        # 匹配 "1." "1．" "1、" 等编号开头
        parts = re.split(r"(?:^|\n)\s*\d+\s*[.．、:：]\s*", claims_text)

        for part in parts:
            part = part.strip()
            if part:
                claims.append(part)

        # 如果上述拆分没有结果，尝试按行拆分
        if not claims:
            lines = [line.strip() for line in claims_text.split("\n") if line.strip()]
            claims = lines

        return claims

    def _heuristic_split(self, text: str) -> PatentDocument:
        """启发式拆分：当文本没有标准段落标记时使用

        策略：
        1. 第一行作为标题
        2. 查找"摘要"关键字附近的内容
        3. 查找"权利要求"关键字附近的内容
        4. 查找"技术领域"关键字附近的内容
        5. 如果都没找到，将全文作为摘要+权利要求
        """
        doc = PatentDocument()
        lines = text.strip().split("\n")

        # 标题：取第一行（如果不太长）
        if lines and len(lines[0].strip()) <= 100:
            doc.title = lines[0].strip()

        # 查找关键段落
        lower_text = text.lower()

        # 摘要
        abstract_match = re.search(
            r"(?:摘\s*要|Abstract)[：:\s]*\n?(.+?)(?=\n\s*\n|权\s*利|技术领域|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if abstract_match:
            doc.abstract = abstract_match.group(1).strip()

        # 技术领域
        field_match = re.search(
            r"(?:技术领域|Technical Field)[：:\s]*\n?(.+?)(?=\n\s*\n|背景|摘要|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if field_match:
            doc.technical_field = field_match.group(1).strip()

        # 背景技术
        bg_match = re.search(
            r"(?:背景技术|Background)[：:\s]*\n?(.+?)(?=\n\s*\n|发明内容|摘要|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if bg_match:
            doc.background = bg_match.group(1).strip()

        # 权利要求
        claims_match = re.search(
            r"(?:权利要求书?|Claims)[：:\s]*\n?(.+?)$",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if claims_match:
            doc.claims = self._parse_claims(claims_match.group(1))

        # 如果都没找到结构化内容，将全文作为摘要（用于分类）
        if not doc.abstract and not doc.claims:
            # 尝试识别权利要求格式的文本（如"一种XXX，包括...，其特征在于..."）
            claim_pattern = re.search(
                r"(一种[^，,]+[，,].+?其特征在于.+)",
                text,
                re.DOTALL
            )
            if claim_pattern:
                doc.claims = [claim_pattern.group(1).strip()]
            else:
                # 将全文作为摘要
                doc.abstract = text.strip()

        return doc
