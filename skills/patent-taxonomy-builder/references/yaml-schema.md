# YAML规则格式完整规范

本文档定义 patent-taxonomy-builder 生成的YAML规则文件的完整格式规范。

---

## 文件命名与路径

- 路径：`patsona/rules/{技术方向id}/taxonomy.yaml`
- 技术方向id：使用英文小写+连字符，如 `battery`、`semi-conductor`、`ai`
- 文件编码：UTF-8

---

## 顶层结构

```yaml
# 专利分类体系规则文件
# 由 patent-taxonomy-builder 自动生成
# 生成时间: 2026-06-08

tech_branch:
  id: "方向id"
  name: "技术方向名称"
  level: 1
  description: "方向描述"

children:
  - id: "子分支id"
    name: "子分支名称"
    level: 2
    keywords:
      must_have: ["必须包含的关键词"]
      any_of: ["至少包含其一"]
      exclude: ["排除关键词"]
    classification_rules:
      - id: "三级分支id"
        name: "三级分支名称"
        level: 3
        criteria:
          - "判定标准1"
          - "判定标准2"
        keywords: ["关键词列表"]
        boundary_rules:
          - condition: "当同时涉及A和B时"
            resolution: "优先归入A分支，因为..."
        sample_patents:
          - patent_id: "CN1234567A"
            title: "专利标题"
            abstract: "摘要前200字"
```

---

## 字段详细说明

### tech_branch（顶层技术方向）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 方向唯一标识，英文小写+连字符 |
| name | string | 是 | 方向中文名称 |
| level | int | 是 | 层级，固定为1 |
| description | string | 是 | 方向描述，50-200字 |

### children（二级分支列表）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 分支唯一标识，格式：`{方向id}-{分支缩写}` |
| name | string | 是 | 分支中文名称 |
| level | int | 是 | 层级，固定为2 |
| keywords | object | 是 | 关键词规则，见下方说明 |
| classification_rules | array | 是 | 三级分支列表 |

### keywords（关键词规则）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| must_have | string[] | 否 | 必须包含至少一个（AND逻辑） |
| any_of | string[] | 是 | 至少包含其中一个（OR逻辑） |
| exclude | string[] | 否 | 包含任一则排除 |

**匹配逻辑：**
```
匹配 = (must_have为空 OR 包含must_have中至少一个)
   AND (包含any_of中至少一个)
   AND (不包含exclude中任何一个)
```

### classification_rules（三级分支）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 分支唯一标识，格式：`{二级id}-{分支缩写}` |
| name | string | 是 | 分支中文名称 |
| level | int | 是 | 层级，固定为3 |
| criteria | string[] | 是 | 判定标准列表，2-5条 |
| keywords | string[] | 是 | 该分支的关键词列表，3-10个 |
| boundary_rules | object[] | 否 | 边界案例处理规则 |
| sample_patents | object[] | 否 | 样本专利列表 |

### boundary_rules（边界规则）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| condition | string | 是 | 边界条件描述 |
| resolution | string | 是 | 处理方式描述 |

### sample_patents（样本专利）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| patent_id | string | 是 | 专利号，如CN1234567A |
| title | string | 是 | 专利标题 |
| abstract | string | 否 | 摘要前200字 |

---

## 四级分支扩展

如需四级细分，在三级分支内增加 `sub_classification_rules` 字段：

```yaml
classification_rules:
  - id: "battery-li-cathode-ncm"
    name: "三元材料"
    level: 3
    criteria:
      - "正极材料包含镍钴锰酸锂"
    keywords: ["NCM", "三元", "镍钴锰"]
    sub_classification_rules:
      - id: "battery-li-cathode-ncm-high"
        name: "高镍三元"
        level: 4
        criteria:
          - "镍含量≥80%"
        keywords: ["高镍", "NCM811", "NCM9055"]
        boundary_rules: []
```

---

## ID命名规范

| 层级 | 格式 | 示例 |
|------|------|------|
| 一级 | `{方向英文}` | `battery` |
| 二级 | `{方向}-{分支缩写}` | `battery-li-ion` |
| 三级 | `{二级id}-{分支缩写}` | `battery-li-ion-cathode` |
| 四级 | `{三级id}-{分支缩写}` | `battery-li-ion-cathode-lfp` |

**缩写规则：**
- 使用英文小写
- 多词用连字符连接
- 尽量简短但可辨识
- 避免纯数字缩写

---

## 完整示例

```yaml
tech_branch:
  id: "battery"
  name: "电池"
  level: 1
  description: "涵盖各类电池技术，包括电化学电池、固态电池、燃料电池等的材料、结构、工艺和应用"

children:
  - id: "battery-li-ion"
    name: "锂离子电池"
    level: 2
    keywords:
      must_have: ["锂离子", "锂电池", "lithium-ion", "li-ion"]
      any_of: ["锂离子电池", "锂电池", "二次锂电池", "锂蓄电池", "lithium battery"]
      exclude: ["固态", "solid-state", "钠离子", "sodium-ion"]
    classification_rules:
      - id: "battery-li-ion-cathode"
        name: "正极材料"
        level: 3
        criteria:
          - "专利核心涉及锂离子电池正极材料的组成、结构或制备"
          - "正极材料包括但不限于磷酸铁锂、三元材料、钴酸锂等"
        keywords: ["正极", "cathode", "LFP", "NCM", "NCA", "磷酸铁锂", "三元", "钴酸锂"]
        boundary_rules:
          - condition: "同时涉及正极和负极材料改进"
            resolution: "按主权利要求所述材料分类；若均为主权项，按创新贡献更大的材料分类"
        sample_patents:
          - patent_id: "CN116599234A"
            title: "一种磷酸铁锂正极材料及其制备方法"
            abstract: "本发明公开了一种磷酸铁锂正极材料，通过掺杂镁元素提高导电性..."

      - id: "battery-li-ion-anode"
        name: "负极材料"
        level: 3
        criteria:
          - "专利核心涉及锂离子电池负极材料的组成、结构或制备"
          - "负极材料包括石墨、硅基、锡基等"
        keywords: ["负极", "anode", "石墨", "硅基", "硅碳", "锡基"]
        boundary_rules:
          - condition: "同时涉及正极和负极材料改进"
            resolution: "按主权利要求所述材料分类"
        sample_patents: []

      - id: "battery-li-ion-electrolyte"
        name: "电解液"
        level: 3
        criteria:
          - "专利核心涉及锂离子电池电解液的组成、添加剂或制备"
        keywords: ["电解液", "electrolyte", "添加剂", "溶剂", "锂盐"]
        boundary_rules: []
        sample_patents: []

  - id: "battery-solid-state"
    name: "固态电池"
    level: 2
    keywords:
      must_have: ["固态", "solid-state"]
      any_of: ["固态电池", "固态电解质", "全固态", "半固态", "solid-state battery"]
      exclude: []
    classification_rules:
      - id: "battery-solid-state-oxide"
        name: "氧化物电解质"
        level: 3
        criteria:
          - "固态电解质为氧化物体系，如LLZO、LATP等"
        keywords: ["氧化物", "LLZO", "LATP", "石榴石", "NASICON"]
        boundary_rules: []
        sample_patents: []

      - id: "battery-solid-state-sulfide"
        name: "硫化物电解质"
        level: 3
        criteria:
          - "固态电解质为硫化物体系，如LPS、Li6PS5Cl等"
        keywords: ["硫化物", "LPS", "Li6PS5Cl", "硫银锗矿"]
        boundary_rules: []
        sample_patents: []

      - id: "battery-solid-state-polymer"
        name: "聚合物电解质"
        level: 3
        criteria:
          - "固态电解质为聚合物体系，如PEO基等"
        keywords: ["聚合物", "PEO", "聚环氧乙烷", "凝胶聚合物"]
        boundary_rules: []
        sample_patents: []
```

---

## 校验规则

### ERROR级别（必须修复）

1. **末端分支无criteria**：每个最细粒度分支必须有至少1条判定标准
2. **分支无keywords**：每个二级分支必须有keywords.any_of
3. **id重复**：所有id必须全局唯一
4. **id格式错误**：不符合命名规范

### WARNING级别（建议修复）

1. **must_have与any_of重叠**：同一关键词不应同时出现在must_have和any_of
2. **跨分支关键词重叠**：不同分支的must_have有交集
3. **末端分支无sample_patents**：建议至少有1条样本
4. **criteria过少**：建议至少2条判定标准
5. **boundary_rules缺失**：相邻分支建议有边界规则

### INFO级别（仅供参考）

1. **层级深度>4**：建议简化
2. **分支数量过多**（>30个末端分支）：建议合并
3. **keywords.any_of过少**（<3个）：建议补充
