"""YAML 规则加载与校验 - 从 rules/ 目录加载分类规则文件"""

from pathlib import Path
from typing import Optional

import yaml

from patsona.extractor.rule_extractor import TechBranchRule


class RuleLoader:
    """分类规则加载器

    从 YAML 文件加载技术分支分类规则，并进行完整性校验。

    支持两种 YAML 格式：
    1. 列表格式：
    ```yaml
    branches:
      - id: "A01"
        name: "数据采集-传感器"
        parent_id: "A"
        keywords: ["传感器", "采集", "检测"]
        criteria: "涉及物理传感器的数据采集技术"
    ```

    2. 嵌套格式（patent-taxonomy-builder生成）：
    ```yaml
    tech_branch:
      id: "battery"
      name: "电池"
      level: 1
      children:
        - id: "battery-li"
          name: "锂电池"
          level: 2
          keywords: ["锂", "电解质"]
          children:
            - id: "battery-li-solid"
              name: "固态锂电池"
              level: 3
              criteria: ["电解质为固态"]
    ```
    """

    # 必填字段
    REQUIRED_FIELDS = ["id", "name"]

    def load_rules(self, rules_dir: Path) -> list[TechBranchRule]:
        """从目录加载所有 YAML 规则文件（递归查找子目录）

        Args:
            rules_dir: 规则文件目录

        Returns:
            技术分支规则列表
        """
        rules: list[TechBranchRule] = []

        if not rules_dir.exists():
            return rules

        # 递归遍历所有 YAML 文件
        yaml_files = list(rules_dir.glob("**/*.yaml")) + list(rules_dir.glob("**/*.yml"))

        for yaml_file in yaml_files:
            file_rules = self._load_single_file(yaml_file)
            rules.extend(file_rules)

        return rules

    def load_and_validate(
        self, rules_dir: Path
    ) -> tuple[list[TechBranchRule], list[str]]:
        """加载规则并校验完整性

        Args:
            rules_dir: 规则文件目录

        Returns:
            (规则列表, 错误信息列表)
        """
        rules = self.load_rules(rules_dir)
        errors = self._validate_rules(rules)
        return rules, errors

    def _load_single_file(self, file_path: Path) -> list[TechBranchRule]:
        """加载单个 YAML 规则文件

        支持两种格式：branches列表格式 和 tech_branch嵌套格式

        Args:
            file_path: YAML 文件路径

        Returns:
            该文件中定义的规则列表
        """
        rules: list[TechBranchRule] = []

        try:
            content = file_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            # YAML 解析错误，跳过该文件
            return rules
        except Exception:
            return rules

        if not data or not isinstance(data, dict):
            return rules

        # 格式1: branches 列表格式
        branches = data.get("branches", [])
        if isinstance(branches, list):
            for branch_data in branches:
                if not isinstance(branch_data, dict):
                    continue
                rule = self._parse_branch(branch_data)
                if rule:
                    rules.append(rule)

        # 格式2: tech_branch 嵌套格式（patent-taxonomy-builder生成）
        tech_branch = data.get("tech_branch", {})
        if tech_branch and isinstance(tech_branch, dict):
            # 解析根节点
            root_rule = self._parse_nested_branch(tech_branch, parent_id="")
            if root_rule:
                rules.append(root_rule)
            # 递归解析子节点（children在顶层，不在tech_branch内）
            children = data.get("children", [])
            if children:
                self._parse_children(children, tech_branch.get("id", ""), rules)

        return rules

    def _parse_children(self, children: list, parent_id: str, rules: list) -> None:
        """递归解析嵌套格式的子节点

        Args:
            children: 子节点列表
            parent_id: 父节点ID
            rules: 规则列表（用于收集结果）
        """
        if not isinstance(children, list):
            return

        for child in children:
            if not isinstance(child, dict):
                continue

            # 解析当前节点
            rule = self._parse_nested_branch(child, parent_id)
            if rule:
                rules.append(rule)

            # 递归解析下一层子节点
            sub_children = child.get("children", [])
            if sub_children:
                self._parse_children(sub_children, child.get("id", ""), rules)

    def _parse_nested_branch(self, data: dict, parent_id: str) -> Optional[TechBranchRule]:
        """解析嵌套格式的分支定义

        Args:
            data: 分支数据字典
            parent_id: 父节点ID

        Returns:
            TechBranchRule 对象，解析失败返回 None
        """
        branch_id = data.get("id", "")
        branch_name = data.get("name", "")

        if not branch_id or not branch_name:
            return None

        # 处理 keywords 字段（可能是列表或 dict）
        keywords = data.get("keywords", [])
        if isinstance(keywords, dict):
            # 格式: {must_have: [], any_of: [], exclude: []}
            keywords = keywords.get("any_of", []) + keywords.get("must_have", [])
        elif not isinstance(keywords, list):
            keywords = []

        # 处理 criteria 字段（可能是列表或字符串）
        criteria = data.get("criteria", "")
        if isinstance(criteria, list):
            criteria = "\n".join(criteria)

        # 处理 classification_rules（三级分支的详细判定标准）
        classification_rules = data.get("classification_rules", [])
        if classification_rules and isinstance(classification_rules, list):
            # 提取每个子规则的 criteria
            for sub_rule in classification_rules:
                if isinstance(sub_rule, dict):
                    sub_criteria = sub_rule.get("criteria", [])
                    if isinstance(sub_criteria, list):
                        criteria += "\n" + "\n".join(sub_criteria)

        rule = TechBranchRule(
            branch_id=str(branch_id),
            branch_name=str(branch_name),
            parent_id=str(parent_id),
            keywords=[str(k) for k in keywords],
            patterns=[str(p) for p in data.get("patterns", []) or []],
            exclude_keywords=[str(k) for k in data.get("exclude_keywords", []) or []],
            criteria=str(criteria),
            detailed_criteria=str(data.get("detailed_criteria", "")),
        )

        return rule

    def _parse_branch(self, data: dict) -> Optional[TechBranchRule]:
        """解析列表格式的分支定义

        Args:
            data: 分支数据字典

        Returns:
            TechBranchRule 对象，解析失败返回 None
        """
        branch_id = data.get("id", "")
        branch_name = data.get("name", "")

        if not branch_id or not branch_name:
            return None

        rule = TechBranchRule(
            branch_id=str(branch_id),
            branch_name=str(branch_name),
            parent_id=str(data.get("parent_id", "")),
            keywords=[str(k) for k in data.get("keywords", []) or []],
            patterns=[str(p) for p in data.get("patterns", []) or []],
            exclude_keywords=[str(k) for k in data.get("exclude_keywords", []) or []],
            criteria=str(data.get("criteria", "")),
            detailed_criteria=str(data.get("detailed_criteria", "")),
        )

        return rule

    def _validate_rules(self, rules: list[TechBranchRule]) -> list[str]:
        """校验规则完整性

        检查项：
        1. 分支ID唯一性
        2. parent_id 引用的分支是否存在
        3. 关键词/正则模式是否为空（警告级别）
        4. criteria 判定标准是否为空（警告级别）

        Args:
            rules: 规则列表

        Returns:
            错误信息列表
        """
        errors: list[str] = []
        branch_ids = {r.branch_id for r in rules}

        # 检查ID唯一性
        seen_ids: dict[str, int] = {}
        for rule in rules:
            count = seen_ids.get(rule.branch_id, 0) + 1
            seen_ids[rule.branch_id] = count
            if count > 1:
                errors.append(f"分支ID重复: {rule.branch_id}")

        # 检查 parent_id 引用
        for rule in rules:
            if rule.parent_id and rule.parent_id not in branch_ids:
                errors.append(
                    f"分支 {rule.branch_id} 的 parent_id '{rule.parent_id}' 不存在"
                )

        # 检查关键词和正则（警告级别，不阻断）
        for rule in rules:
            if not rule.keywords and not rule.patterns:
                errors.append(
                    f"警告: 分支 {rule.branch_id}({rule.branch_name}) "
                    "没有定义关键词和正则模式，Layer1无法匹配"
                )
            if not rule.criteria:
                errors.append(
                    f"警告: 分支 {rule.branch_id}({rule.branch_name}) "
                    "没有定义判定标准(criteria)，Layer2/3无法使用"
                )

        return errors