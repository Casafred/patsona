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

    # 独权分析系统角色
    CLAIM_ANALYZER_ROLE = (
        "你是一位资深的专利权利要求分析专家，精通各国专利权利要求的撰写规则和保护范围解读，"
        "熟悉中文、英文、日文、韩文等各种语言的专利权利要求表达方式。"
        "你的任务是：从给定的全部权利要求中识别出独立权利要求和从属权利要求，"
        "对每条独立权利要求进行深度分析，提取保护主题和关键技术特征，"
        "对比各独权之间的异同，并标识出保护方向明显不同的异常独权。"
        "你需要严格按照指定的JSON格式输出结果，分析必须基于权利要求的原文，不得臆造。"
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

    def get_claim_analysis_prompt(
        self,
        all_claims: list[dict],
    ) -> list[dict]:
        """构建权利要求分析的 Prompt

        传入全部权利要求，由 LLM 识别独权/从权并进行分析。

        Args:
            all_claims: 全部权利要求列表，
                每项格式 {"claim_number": int, "text": str}

        Returns:
            消息列表
        """
        claims_desc = self._format_all_claims(all_claims)
        total_count = len(all_claims)

        user_content = f"""请对以下权利要求书进行分析，识别独立权利要求与从属权利要求，并对各独立权利要求进行深度分析。

## 权利要求书（共{total_count}条）
{claims_desc}

## 分析要求

### 第一步：识别独立权利要求和从属权利要求

判断标准：**如果某条权利要求引用了（依赖了）其他权利要求，则为从属权利要求；否则为独立权利要求。**

常见的从属权利要求引用表达（不限语言）：
- 中文："根据权利要求X所述的"、"如权利要求X所述的"、"按照权利要求X"
- 英文："according to claim X"、"as recited in claim X"、"of claim X"、"as set forth in claim X"
- 日文："請求項Xに記載の"、"請求項Xに従う"
- 韩文："청구항 X에 따른"、"청구항 X에 기재된"
- 其他语言中任何形式的对其他权利要求的引用

注意：
- 引用多个权利要求的也是从权（如"根据权利要求1-3所述的"）
- 仅引用其他权利要求的编号即构成从权，无论引用方式如何
- 独立权利要求不引用任何其他权利要求，其保护范围自成一体

对每条从属权利要求，需记录其引用的权利要求编号（references）。

### 第二步：逐条解析各独立权利要求
对每条独立权利要求，提取以下信息：
1. **protection_subject**（保护主题）：权利要求前序部分定义的保护对象，如"一种电动螺丝批"、"一种控制方法"、"一种存储介质"
2. **subject_category**（主题类别）：从以下选项中选择最匹配的：
   - "产品" — 实体装置、设备、器具、系统、组件等
   - "方法" — 制造方法、控制方法、处理方法、检测方法等
   - "用途" — 应用用途类权利要求
   - "介质" — 存储介质、计算机可读介质等
   - "组合" — 同时包含产品和方法特征的权利要求
3. **key_features**（关键技术特征）：列出该独权中定义的、构成其保护范围的必要技术特征，每条特征用简练的一句话概括
4. **technical_problem**（解决的技术问题）：根据权利要求的技术特征推断其解决的技术问题
5. **protection_scope_summary**（保护范围概述）：用1-2句话概括该独权的保护范围边界

### 第三步：对比分析所有独立权利要求
1. **common_features**（共同点）：列出各独权之间共享的技术特征、相同的保护方向或技术路线
2. **differences**（差异点）：逐对比较各独权之间的关键差异，每条差异需指明涉及的权利要求编号
3. **outlier_claims**（异常独权标识）：对于满足以下任一条件的独权，必须标记为outlier：
   - 保护主题类别与其他独权不同（如其他独权保护产品，该独权保护方法）
   - 技术路线/解决手段与其他独权属于不同技术领域
   - 保护方向与其他独权明显不同，不属于同一发明构思下的并行保护
   对于每条outlier，需说明差异类型（主题差异/技术路线差异/应用场景差异等）、差异原因、以及该独权独特的保护方向

### 第四步：总体概述
用2-3句话总结该专利独立权利要求的整体布局策略，包括独权之间的关系（互补/平行/递进等）和保护范围覆盖情况。

## 输出格式
```json
{{
    "independent_claims": [
        {{
            "claim_number": 1,
            "protection_subject": "一种XXX",
            "subject_category": "产品",
            "key_features": ["特征1", "特征2", "特征3"],
            "technical_problem": "解决的技术问题",
            "protection_scope_summary": "保护范围概述"
        }}
    ],
    "dependent_claims": [
        {{
            "claim_number": 2,
            "references": [1]
        }}
    ],
    "comparison": {{
        "common_features": ["共同点1", "共同点2"],
        "differences": [
            {{
                "claim_numbers": [1, 5],
                "difference": "差异描述"
            }}
        ],
        "outlier_claims": [
            {{
                "claim_number": 9,
                "divergence_type": "主题差异",
                "reason": "差异原因说明",
                "unique_direction": "该独权独特的保护方向"
            }}
        ]
    }},
    "summary": "总体分析概述"
}}
```

注意：
- independent_claims 和 dependent_claims 的编号之和必须等于总权利要求数，不可遗漏
- key_features 应提取权利要求中的必要技术特征，而非简单复述原文
- 如果所有独权保护方向一致，outlier_claims 可以为空数组
- differences 应涵盖所有值得关注的差异，不要遗漏
- 分析必须严格基于权利要求原文，不得推测未记载的内容"""

        return [
            {"role": "system", "content": self.CLAIM_ANALYZER_ROLE},
            {"role": "user", "content": user_content},
        ]

    def _format_all_claims(self, claims: list[dict]) -> str:
        """格式化全部权利要求描述"""
        lines: list[str] = []
        for c in claims:
            num = c.get("claim_number", "?")
            text = c.get("text", "")
            lines.append(f"### 权利要求{num}")
            lines.append(f"{text}")
            lines.append("")
        return "\n".join(lines)
