"""分类树构建与遍历 - 将扁平的分支列表构建为层级树结构"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from rich.tree import Tree

from patsona.extractor.rule_extractor import TechBranchRule


@dataclass
class TreeNode:
    """分类树节点"""

    # 分支ID
    branch_id: str
    # 分支名称
    branch_name: str
    # 子节点列表
    children: list["TreeNode"] = field(default_factory=list)
    # 父节点（构建后设置）
    parent: Optional["TreeNode"] = field(default=None, repr=False)
    # 关联的规则
    rule: Optional[TechBranchRule] = field(default=None, repr=False)
    # 层级深度（根节点为0）
    depth: int = 0


class ClassificationTree:
    """分类树

    将扁平的技术分支列表构建为层级树结构，
    支持按层级查询、遍历等操作。
    """

    def __init__(self) -> None:
        # 根节点列表（可能有多个顶级分类）
        self.roots: list[TreeNode] = []
        # ID 到节点的快速索引
        self._node_map: dict[str, TreeNode] = {}

    def build(self, branches: list[TechBranchRule]) -> "ClassificationTree":
        """从扁平分支列表构建树结构

        Args:
            branches: 技术分支规则列表

        Returns:
            self（支持链式调用）
        """
        # 清空旧数据
        self.roots = []
        self._node_map = {}

        # 第一步：创建所有节点
        for branch in branches:
            node = TreeNode(
                branch_id=branch.branch_id,
                branch_name=branch.branch_name,
                rule=branch,
            )
            self._node_map[branch.branch_id] = node

        # 第二步：建立父子关系
        for branch in branches:
            node = self._node_map[branch.branch_id]

            if branch.parent_id and branch.parent_id in self._node_map:
                # 有父节点，挂到父节点下
                parent_node = self._node_map[branch.parent_id]
                parent_node.children.append(node)
                node.parent = parent_node
                node.depth = parent_node.depth + 1
            else:
                # 无父节点或父节点不存在，作为根节点
                self.roots.append(node)
                node.depth = 0

        return self

    def get_candidates(
        self, level: int, parent_id: Optional[str] = None
    ) -> list[TreeNode]:
        """获取指定层级、指定父节点下的候选节点

        Args:
            level: 目标层级（0为根层级）
            parent_id: 父节点ID，None表示从根开始

        Returns:
            匹配的节点列表
        """
        if parent_id:
            parent = self._node_map.get(parent_id)
            if not parent:
                return []
            # 在父节点的子节点中查找指定层级
            return self._find_by_level(parent, level - parent.depth - 1)
        else:
            # 从根开始查找
            results: list[TreeNode] = []
            for root in self.roots:
                results.extend(self._find_by_level(root, level))
            return results

    def _find_by_level(self, node: TreeNode, remaining_levels: int) -> list[TreeNode]:
        """递归查找指定层级的节点"""
        if remaining_levels == 0:
            return [node]
        if remaining_levels < 0:
            return []

        results: list[TreeNode] = []
        for child in node.children:
            results.extend(self._find_by_level(child, remaining_levels - 1))
        return results

    def traverse(self, callback: Callable[[TreeNode], None]) -> None:
        """深度优先遍历整棵树

        Args:
            callback: 对每个节点调用的回调函数
        """
        for root in self.roots:
            self._traverse_node(root, callback)

    def _traverse_node(
        self, node: TreeNode, callback: Callable[[TreeNode], None]
    ) -> None:
        """递归遍历节点"""
        callback(node)
        for child in node.children:
            self._traverse_node(child, callback)

    def get_node(self, branch_id: str) -> Optional[TreeNode]:
        """根据ID获取节点"""
        return self._node_map.get(branch_id)

    def get_children(self, branch_id: str) -> list[TreeNode]:
        """获取指定节点的直接子节点"""
        node = self._node_map.get(branch_id)
        if node:
            return node.children
        return []

    def get_path(self, branch_id: str) -> list[TreeNode]:
        """获取从根到指定节点的路径

        Args:
            branch_id: 目标节点ID

        Returns:
            从根到目标的节点路径列表
        """
        node = self._node_map.get(branch_id)
        if not node:
            return []

        path: list[TreeNode] = []
        current = node
        while current:
            path.append(current)
            current = current.parent

        path.reverse()
        return path

    def summary(self) -> Tree:
        """生成 Rich Tree 格式的分类树概览

        Returns:
            Rich Tree 对象，可直接用 console.print() 输出
        """
        tree = Tree("专利分类树")

        for root in self.roots:
            self._build_rich_tree(tree, root)

        return tree

    def _build_rich_tree(self, parent: Tree, node: TreeNode) -> None:
        """递归构建 Rich Tree"""
        label = f"{node.branch_name} [dim]({node.branch_id})[/dim]"
        branch = parent.add(label)

        for child in node.children:
            self._build_rich_tree(branch, child)

    @property
    def total_nodes(self) -> int:
        """树中节点总数"""
        return len(self._node_map)

    @property
    def max_depth(self) -> int:
        """树的最大深度"""
        if not self.roots:
            return 0

        max_d = 0
        for root in self.roots:
            max_d = max(max_d, self._get_max_depth(root))
        return max_d

    def _get_max_depth(self, node: TreeNode) -> int:
        """递归计算最大深度"""
        if not node.children:
            return node.depth
        return max(self._get_max_depth(child) for child in node.children)
