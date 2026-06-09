"""专利文档解析器 - 支持 PDF/DOCX/TXT 格式的专利文档解析"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
from docx import Document


@dataclass
class PatentDocument:
    """解析后的专利文档结构"""

    # 发明名称
    title: str = ""
    # 摘要
    abstract: str = ""
    # 权利要求列表（第1项为独立权利要求）
    claims: list[str] = field(default_factory=list)
    # 技术领域
    technical_field: str = ""
    # 背景技术
    background: str = ""
    # 原始全文（备用）
    raw_text: str = ""

    @property
    def claim1(self) -> str:
        """获取权利要求1（独立权利要求）"""
        return self.claims[0] if self.claims else ""

    @property
    def summary_text(self) -> str:
        """用于分类的核心文本：摘要 + 权利要求1"""
        parts = []
        if self.abstract:
            parts.append(f"【摘要】{self.abstract}")
        if self.claim1:
            parts.append(f"【权利要求1】{self.claim1}")
        return "\n".join(parts)

    @property
    def full_text(self) -> str:
        """完整文本：标题+技术领域+背景+摘要+权利要求"""
        parts = []
        if self.title:
            parts.append(f"【发明名称】{self.title}")
        if self.technical_field:
            parts.append(f"【技术领域】{self.technical_field}")
        if self.background:
            parts.append(f"【背景技术】{self.background}")
        if self.abstract:
            parts.append(f"【摘要】{self.abstract}")
        if self.claims:
            claims_text = "\n".join(
                f"  {i+1}. {c}" for i, c in enumerate(self.claims)
            )
            parts.append(f"【权利要求】\n{claims_text}")
        return "\n\n".join(parts)


class PatentParser:
    """专利文档解析器，支持 PDF / DOCX / TXT 格式"""

    def parse_file(self, path: Path) -> PatentDocument:
        """根据文件扩展名自动选择解析方法"""
        path = Path(path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self.parse_pdf(path)
        elif suffix in (".docx", ".doc"):
            return self.parse_docx(path)
        elif suffix in (".txt", ".text"):
            return self.parse_txt(path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}，仅支持 PDF/DOCX/TXT")

    def parse_text(self, text: str) -> PatentDocument:
        """解析粘贴的专利文本，尝试提取结构化字段"""
        from patsona.preprocessor.splitter import PatentSplitter

        splitter = PatentSplitter()
        return splitter.split_sections(text)

    def parse_pdf(self, path: Path) -> PatentDocument:
        """解析 PDF 格式的专利文档"""
        full_text = self._extract_pdf_text(path)
        from patsona.preprocessor.splitter import PatentSplitter

        splitter = PatentSplitter()
        doc = splitter.split_sections(full_text)
        doc.raw_text = full_text
        return doc

    def parse_docx(self, path: Path) -> PatentDocument:
        """解析 DOCX 格式的专利文档"""
        full_text = self._extract_docx_text(path)
        from patsona.preprocessor.splitter import PatentSplitter

        splitter = PatentSplitter()
        doc = splitter.split_sections(full_text)
        doc.raw_text = full_text
        return doc

    def parse_txt(self, path: Path) -> PatentDocument:
        """解析 TXT 格式的专利文档"""
        full_text = path.read_text(encoding="utf-8")
        from patsona.preprocessor.splitter import PatentSplitter

        splitter = PatentSplitter()
        doc = splitter.split_sections(full_text)
        doc.raw_text = full_text
        return doc

    def _extract_pdf_text(self, path: Path) -> str:
        """从 PDF 文件提取纯文本"""
        text_parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_docx_text(self, path: Path) -> str:
        """从 DOCX 文件提取纯文本"""
        doc = Document(str(path))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs)
