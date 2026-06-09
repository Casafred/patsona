"""分类API - 调用patsona分类引擎"""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

# 导入patsona模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from patsona.classifier.engine import ClassificationEngine
from patsona.preprocessor.parser import PatentParser
from patsona.rules.loader import RuleLoader
from patsona.config import settings

router = APIRouter(prefix="/api/classify", tags=["classify"])

# 全局规则缓存
_rules_cache = None
_rules_errors = None


def get_rules():
    """获取分类规则（带缓存）"""
    global _rules_cache, _rules_errors
    if _rules_cache is None:
        loader = RuleLoader()
        rules_path = settings.rules_path
        _rules_cache, _rules_errors = loader.load_and_validate(rules_path)
    return _rules_cache, _rules_errors


def clear_rules_cache():
    """清除规则缓存"""
    global _rules_cache, _rules_errors
    _rules_cache = None
    _rules_errors = None


class ClassifyRequest(BaseModel):
    """分类请求"""
    text: str
    model_override: Optional[str] = None


class BatchClassifyRequest(BaseModel):
    """批量分类请求"""
    texts: list[str]
    model_override: Optional[str] = None


class PathStepModel(BaseModel):
    """分类路径节点"""
    branch_id: str
    branch_name: str
    level: int
    method: str = ""
    confidence: float = 0.0
    reasoning: str = ""


class BatchClassifyResult(BaseModel):
    """单条批量分类结果"""
    index: int
    branch_id: str
    branch_name: str
    path_display: str = ""
    confidence: float
    reasoning: str
    needs_review: bool


class BatchClassifyResponse(BaseModel):
    """批量分类响应"""
    success: bool
    total: int = 0
    results: list[BatchClassifyResult] = []
    error: str = ""


class ClassifyResponse(BaseModel):
    """分类响应"""
    success: bool
    branch_id: str = ""
    branch_name: str = ""
    # 完整分类路径
    path: list[PathStepModel] = []
    # 路径描述：如 "按压启动 > 单一按压启动 > 机械开关触发"
    path_display: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    needs_review: bool = False
    error: str = ""


def _build_response(result) -> ClassifyResponse:
    """从ClassificationResult构建API响应"""
    path = [
        PathStepModel(
            branch_id=p.branch_id,
            branch_name=p.branch_name,
            level=p.level,
            method=p.method,
            confidence=p.confidence,
            reasoning=p.reasoning,
        )
        for p in result.path
    ]

    return ClassifyResponse(
        success=True,
        branch_id=result.branch_id,
        branch_name=result.branch_name,
        path=path,
        path_display=result.path_display,
        confidence=result.confidence,
        reasoning=result.reasoning,
        needs_review=result.needs_review,
    )


@router.post("", response_model=ClassifyResponse)
async def classify_text(request: ClassifyRequest):
    """对文本进行分类"""
    try:
        # 获取规则
        rules, errors = get_rules()
        if not rules:
            return ClassifyResponse(
                success=False,
                error=f"未加载到分类规则: {'; '.join(errors) if errors else '规则目录为空'}"
            )

        # 解析文本
        parser = PatentParser()
        patent_doc = parser.parse_text(request.text)

        if not patent_doc.summary_text.strip():
            return ClassifyResponse(
                success=False,
                error="无法从文本中提取有效内容，请确保包含摘要或权利要求"
            )

        # 执行分类
        engine = ClassificationEngine(model_override=request.model_override)
        result = engine.classify(patent_doc, rules)

        return _build_response(result)

    except Exception as e:
        return ClassifyResponse(
            success=False,
            error=f"分类过程出错: {str(e)}"
        )


@router.post("/batch", response_model=BatchClassifyResponse)
async def classify_batch(request: BatchClassifyRequest):
    """批量分类多条文本"""
    try:
        # 获取规则
        rules, errors = get_rules()
        if not rules:
            return BatchClassifyResponse(
                success=False,
                error=f"未加载到分类规则: {'; '.join(errors) if errors else '规则目录为空'}"
            )

        results = []
        parser = PatentParser()
        engine = ClassificationEngine(model_override=request.model_override)

        for idx, text in enumerate(request.texts):
            try:
                patent_doc = parser.parse_text(text)
                if patent_doc.summary_text.strip():
                    result = engine.classify(patent_doc, rules)
                    results.append(BatchClassifyResult(
                        index=idx,
                        branch_id=result.branch_id,
                        branch_name=result.branch_name,
                        path_display=result.path_display,
                        confidence=result.confidence,
                        reasoning=result.reasoning,
                        needs_review=result.needs_review
                    ))
                else:
                    results.append(BatchClassifyResult(
                        index=idx,
                        branch_id="PARSE_ERROR",
                        branch_name="解析失败",
                        confidence=0.0,
                        reasoning="无法提取有效内容",
                        needs_review=True
                    ))
            except Exception as e:
                results.append(BatchClassifyResult(
                    index=idx,
                    branch_id="ERROR",
                    branch_name="分类出错",
                    confidence=0.0,
                    reasoning=str(e),
                    needs_review=True
                ))

        return BatchClassifyResponse(
            success=True,
            total=len(request.texts),
            results=results
        )

    except Exception as e:
        return BatchClassifyResponse(
            success=False,
            error=f"批量分类出错: {str(e)}"
        )


@router.post("/upload", response_model=ClassifyResponse)
async def classify_file(file: UploadFile = File(...)):
    """上传文件并分类"""
    try:
        # 检查文件类型
        suffix = Path(file.filename).suffix.lower()
        if suffix not in [".pdf", ".docx", ".doc", ".txt"]:
            return ClassifyResponse(
                success=False,
                error=f"不支持的文件格式: {suffix}，仅支持 PDF/DOCX/TXT"
            )

        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            # 解析文件
            parser = PatentParser()
            patent_doc = parser.parse_file(tmp_path)

            if not patent_doc.summary_text.strip():
                return ClassifyResponse(
                    success=False,
                    error="无法从文件中提取有效内容，请确保包含摘要或权利要求"
                )

            # 获取规则
            rules, errors = get_rules()
            if not rules:
                return ClassifyResponse(
                    success=False,
                    error=f"未加载到分类规则: {'; '.join(errors) if errors else '规则目录为空'}"
                )

            # 执行分类
            engine = ClassificationEngine()
            result = engine.classify(patent_doc, rules)

            return _build_response(result)

        finally:
            # 清理临时文件
            tmp_path.unlink(missing_ok=True)

    except Exception as e:
        return ClassifyResponse(
            success=False,
            error=f"文件处理出错: {str(e)}"
        )
