"""Prompt 模板管理 - 所有 LLM Prompt 集中管理"""

from patsona.classifier.types import CandidateBranch, ScoredBranch
from patsona.preprocessor.parser import PatentDocument


class PromptManager:
    """Prompt 模板管理器

    集中管理所有分类流程中的 Prompt 模板，
    确保提示词的一致性和可维护性。
    """

    # 系统角色描述
    SYSTEM_ROLE = (
        "你是一位资深的专利分类专家，精通各技术领域的专利分类标准。"
        "你的任务是根据专利文本内容，将其归类到正确的技术分支。"
        "你需要严格按照指定的JSON格式输出结果。"
    )

    def get_layer2_prompt(
        self,
        patent_doc: PatentDocument,
        candidates: list[CandidateBranch],
    ) -> list[dict]:
        """构建 Layer2 中分类的 Prompt

        传入专利摘要+权利要求1，以及候选分支的判定标准，
        要求 LLM 对每个候选给出置信度评分。
        """
        candidates_desc = self._format_candidates(candidates)

        patent_text = patent_doc.summary_text
        if not patent_text.strip():
            patent_text = patent_doc.full_text

        user_content = f"""请对以下专利进行技术分支分类判定。

## 专利文本
{patent_text}

## 候选技术分支
{candidates_desc}

## 任务要求
1. 对每个候选分支，根据其判定标准，评估该专利属于该分支的置信度（0.0~1.0）
2. 给出判定依据，说明为什么匹配或不匹配
3. 列出匹配的关键技术特征
4. 按置信度从高到低排列

## 输出格式
```json
{{
    "classifications": [
        {{
            "branch_id": "分支ID",
            "branch_name": "分支名称",
            "confidence": 0.85,
            "reasoning": "判定依据",
            "key_features": ["特征1", "特征2"]
        }}
    ]
}}
```"""

        return [
            {"role": "system", "content": self.SYSTEM_ROLE},
            {"role": "user", "content": user_content},
        ]

    def get_layer3_prompt(
        self,
        patent_doc: PatentDocument,
        candidates: list[ScoredBranch],
        samples: list[dict],
    ) -> list[dict]:
        """构建 Layer3 细分类的 Prompt

        传入专利全文、候选分支详细判定标准、样本专利对比，
        要求 LLM 给出最终分类判定。
        """
        candidates_desc = self._format_scored_candidates(candidates)
        samples_desc = self._format_samples(samples)
        patent_text = patent_doc.full_text

        user_content = f"""请对以下专利进行精细分类判定。Layer2分类的置信度不足，需要你进行更细致的判定。

## 专利全文
{patent_text}

## Layer2 候选分支（需进一步区分）
{candidates_desc}

## 参考样本专利
{samples_desc}

## 任务要求
1. 仔细对比专利技术与各候选分支的详细判定标准
2. 参考样本专利的分类结果进行类比判断
3. 给出最终分类结果，置信度（0.0~1.0），和详细判定依据
4. 列出区分性特征（帮助区分相似分支的关键特征）
5. 如果参考了样本专利，列出参考的样本ID

## 输出格式
```json
{{
    "branch_id": "最终分支ID",
    "branch_name": "最终分支名称",
    "confidence": 0.9,
    "reasoning": "详细判定依据",
    "distinguishing_features": ["区分特征1", "区分特征2"],
    "referenced_samples": ["参考的样本专利ID"]
}}
```"""

        return [
            {"role": "system", "content": self.SYSTEM_ROLE},
            {"role": "user", "content": user_content},
        ]

    def _format_candidates(self, candidates: list[CandidateBranch]) -> str:
        """格式化候选分支描述（Layer2使用）"""
        lines: list[str] = []
        for i, c in enumerate(candidates, 1):
            lines.append(f"### 候选{i}: {c.branch_name} (ID: {c.branch_id})")
            if c.matched_keywords:
                lines.append(f"- 已命中关键词: {', '.join(c.matched_keywords)}")
            lines.append(f"- 规则匹配度: {c.score:.2f}")
            lines.append("")
        return "\n".join(lines)

    def _format_scored_candidates(self, candidates: list[ScoredBranch]) -> str:
        """格式化带置信度的候选分支描述（Layer3使用）"""
        lines: list[str] = []
        for i, c in enumerate(candidates, 1):
            lines.append(f"### 候选{i}: {c.branch_name} (ID: {c.branch_id})")
            lines.append(f"- Layer2置信度: {c.confidence:.2f}")
            if c.reasoning:
                lines.append(f"- Layer2判定: {c.reasoning}")
            if c.key_features:
                lines.append(f"- 匹配特征: {', '.join(c.key_features)}")
            lines.append("")
        return "\n".join(lines)

    def _format_samples(self, samples: list[dict]) -> str:
        """格式化样本专利描述"""
        if not samples:
            return "（暂无样本专利）"

        lines: list[str] = []
        for s in samples:
            lines.append(f"- [{s.get('patent_id', 'N/A')}] {s.get('title', 'N/A')}")
            lines.append(f"  分类: {s.get('branch_id', 'N/A')}")
            abstract = s.get("abstract", "")
            if abstract:
                lines.append(f"  摘要: {abstract[:150]}...")
            lines.append("")
        return "\n".join(lines)
