"""规则API - 获取分类规则树"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 导入patsona模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from patsona.rules.loader import RuleLoader
from patsona.rules.tree import ClassificationTree
from patsona.config import settings

router = APIRouter(prefix="/api/rules", tags=["rules"])


class RuleNode(BaseModel):
    """规则树节点"""
    branch_id: str
    branch_name: str
    parent_id: Optional[str] = None
    keywords: list[str] = []
    patterns: list[str] = []
    criteria: str = ""
    children: list["RuleNode"] = []


class RulesResponse(BaseModel):
    """规则响应"""
    success: bool
    total_count: int = 0
    rules: list[RuleNode] = []
    errors: list[str] = []


def build_rule_tree(rules) -> list[RuleNode]:
    """构建规则树结构"""
    # 创建ID到规则的映射
    rule_map = {r.branch_id: r for r in rules}

    # 创建节点映射
    node_map = {}
    for r in rules:
        node_map[r.branch_id] = RuleNode(
            branch_id=r.branch_id,
            branch_name=r.branch_name,
            parent_id=r.parent_id if r.parent_id else None,
            keywords=r.keywords,
            patterns=r.patterns,
            criteria=r.criteria,
            children=[]
        )

    # 构建树结构
    roots = []
    for r in rules:
        node = node_map[r.branch_id]
        if r.parent_id and r.parent_id in node_map:
            parent_node = node_map[r.parent_id]
            parent_node.children.append(node)
        else:
            roots.append(node)

    return roots


@router.get("", response_model=RulesResponse)
async def get_rules():
    """获取所有分类规则"""
    try:
        loader = RuleLoader()
        rules_path = settings.rules_path
        rules, errors = loader.load_and_validate(rules_path)

        if not rules:
            return RulesResponse(
                success=False,
                errors=errors or ["未找到任何规则文件"]
            )

        # 构建树结构
        rule_tree = build_rule_tree(rules)

        return RulesResponse(
            success=True,
            total_count=len(rules),
            rules=rule_tree,
            errors=errors  # 包含警告信息
        )

    except Exception as e:
        return RulesResponse(
            success=False,
            errors=[f"加载规则失败: {str(e)}"]
        )


@router.get("/tree")
async def get_rules_tree():
    """获取规则树的文本表示"""
    try:
        loader = RuleLoader()
        rules_path = settings.rules_path
        rules, errors = loader.load_and_validate(rules_path)

        if not rules:
            return {"success": False, "error": "未找到任何规则文件"}

        # 构建树
        tree = ClassificationTree()
        tree.build(rules)

        # 生成树形文本
        lines = []
        for root in tree.roots:
            _render_tree_node(root, lines, "")

        return {
            "success": True,
            "tree_text": "\n".join(lines),
            "total_count": len(rules),
            "max_depth": tree.max_depth
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def _render_tree_node(node, lines: list, prefix: str):
    """递归渲染树节点"""
    lines.append(f"{prefix}├── {node.branch_name} ({node.branch_id})")
    for i, child in enumerate(node.children):
        is_last = (i == len(node.children) - 1)
        child_prefix = prefix + ("    " if is_last else "│   ")
        _render_tree_node(child, lines, child_prefix)