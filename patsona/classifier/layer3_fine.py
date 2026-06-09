"""Layer3 细分类 - 调用LLM，传入详细判定标准+样本对比，返回最终分类+置信度+判定依据"""

from typing import Optional

from patsona.classifier.types import FinalResult, ScoredBranch
from patsona.llm.client import LLMClient
from patsona.llm.parser import LLMOutputParser
from patsona.llm.prompts import PromptManager
from patsona.preprocessor.parser import PatentDocument


class Layer3Fine:
    """Layer3 细分类器

    触发条件：Layer2 最高置信度低于阈值时触发

    核心策略：
    1. 传入专利全文 + Layer2 候选的详细判定标准
    2. 传入样本专利作为对比参考
    3. LLM 进行精细判定，给出最终分类 + 置信度 + 判定依据

    Args:
        model_override: 可选的模型覆盖
    """

    def __init__(self, model_override: Optional[str] = None) -> None:
        self.llm_client = LLMClient(model_override=model_override)
        self.prompt_manager = PromptManager()
        self.output_parser = LLMOutputParser()

    def classify(
        self,
        patent_doc: PatentDocument,
        candidates: list[ScoredBranch],
    ) -> FinalResult:
        """执行细分类

        Args:
            patent_doc: 解析后的专利文档
            candidates: Layer2 输出的候选分支列表

        Returns:
            FinalResult 最终分类结果
        """
        if not candidates:
            return FinalResult(
                branch_id="UNCATEGORIZED",
                branch_name="未分类",
                confidence=0.0,
                reasoning="无候选分支可供细分类",
            )

        # 加载样本数据（如果有）
        samples = self._load_samples(candidates)

        # 构建 Prompt
        messages = self.prompt_manager.get_layer3_prompt(patent_doc, candidates, samples)

        # 调用 LLM
        try:
            response_text = self.llm_client.chat_json(messages)
            parsed = self.output_parser.parse_json(response_text)
        except Exception as e:
            print(f"[DEBUG] Layer3 LLM调用失败: {type(e).__name__}: {e}")
            best = candidates[0]
            return FinalResult(
                branch_id=best.branch_id,
                branch_name=best.branch_name,
                confidence=best.confidence * 0.8,
                reasoning="LLM调用失败，基于Layer2结果回退",
            )

        return self._parse_llm_output(parsed, candidates)

    def _parse_llm_output(
        self,
        parsed: dict,
        candidates: list[ScoredBranch],
    ) -> FinalResult:
        """解析 LLM 返回的 JSON 结构"""
        branch_id = parsed.get("branch_id", "")
        branch_name = parsed.get("branch_name", "")
        confidence = float(parsed.get("confidence", 0.0))
        reasoning = parsed.get("reasoning", "")
        distinguishing_features = parsed.get("distinguishing_features", [])
        referenced_samples = parsed.get("referenced_samples", [])

        confidence = max(0.0, min(1.0, confidence))

        if not branch_id and candidates:
            best = candidates[0]
            branch_id = best.branch_id
            branch_name = best.branch_name

        return FinalResult(
            branch_id=branch_id,
            branch_name=branch_name,
            confidence=confidence,
            reasoning=reasoning,
            distinguishing_features=distinguishing_features,
            referenced_samples=referenced_samples,
        )

    def _load_samples(self, candidates: list[ScoredBranch]) -> list[dict]:
        """加载候选分支的样本专利"""
        samples: list[dict] = []

        try:
            from patsona.sample.excel_loader import ExcelSampleLoader
            from patsona.config import settings

            loader = ExcelSampleLoader()
            sample_path = settings.rules_path / "samples.xlsx"
            if sample_path.exists():
                all_samples = loader.load(sample_path)
                candidate_ids = {c.branch_id for c in candidates}
                for s in all_samples:
                    if s.branch_id in candidate_ids:
                        samples.append({
                            "patent_id": s.patent_id,
                            "title": s.title,
                            "abstract": s.abstract[:200],
                            "branch_id": s.branch_id,
                        })
        except Exception:
            pass

        return samples[:10]
