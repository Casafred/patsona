# Patsona - 专利细分分类系统

基于递进式分层分类策略的专利技术分支分类工具，调用大模型 API 完成专利文本的自动分类。

## 核心特性

- **递进式三层分类**：规则匹配 → LLM 中分类 → LLM 细分类，逐层细化
- **规则 + LLM 融合**：关键词/正则规则快速筛选，LLM 语义理解精准判定
- **层级分类树**：支持多级技术分支树，自动从根到叶逐层定位
- **多模型支持**：OpenAI / DeepSeek / 智谱，统一 HTTP 调用，无需 SDK
- **多格式输入**：PDF / DOCX / TXT / Excel，自动解析专利文档结构
- **CLI + Web 双模式**：命令行批量处理，Web 界面交互操作

## 系统架构

```
patsona/
├── classifier/          # 分类引擎（核心）
│   ├── engine.py        # 递进式逐层分类引擎，从根到叶逐层细分
│   ├── layer1_coarse.py # Layer1 粗分类 - 纯规则关键词匹配
│   ├── layer2_medium.py # Layer2 中分类 - LLM + 判定标准
│   ├── layer3_fine.py   # Layer3 细分类 - LLM + 样本对比
│   ├── confidence.py    # 置信度融合计算（规则 0.2 + LLM 0.8）
│   └── types.py         # 数据类型定义
├── extractor/           # 规则特征提取
│   └── rule_extractor.py # 关键词/正则匹配，计算匹配度得分
├── llm/                 # LLM 调用层
│   ├── client.py        # 统一 HTTP 客户端，支持 OpenAI/DeepSeek/智谱
│   ├── prompts.py       # Prompt 模板集中管理
│   └── parser.py        # LLM 输出解析（JSON 提取与修复）
├── preprocessor/        # 专利文档预处理
│   ├── parser.py        # 多格式解析器（PDF/DOCX/TXT）
│   └── splitter.py      # 专利文本结构化拆分（摘要/权利要求/技术领域）
├── rules/               # 分类规则管理
│   ├── loader.py        # YAML 规则加载与校验
│   └── tree.py          # 分类树构建与遍历
├── sample/              # 样本数据
│   └── excel_loader.py  # Excel 样本专利导入
├── reporter/            # 结果输出
│   ├── formatter.py     # 单条/批量/Markdown 格式化
│   └── stats.py         # 批量统计分析
├── config.py            # 配置管理（pydantic-settings + .env）
└── cli.py               # CLI 入口（Typer + Rich）
```

```
web/
├── backend/             # FastAPI 后端
│   ├── main.py          # 应用入口 + SPA 中间件
│   └── routes/
│       ├── classify.py  # 分类 API（单条/批量/文件上传）
│       ├── config.py    # 配置管理 API
│       ├── rules.py     # 规则树查询 API
│       └── upload.py    # 文件上传与 Excel 处理 API
└── frontend/            # Vue 3 前端
    └── src/
        ├── App.vue              # 主布局（侧栏配置 + 主内容区）
        └── components/
            ├── ConfigPanel.vue  # API Key / 模型配置面板
            ├── UploadZone.vue   # 文件上传区域
            ├── ResultDisplay.vue # 分类结果展示
            ├── RuleTree.vue     # 规则树展示
            └── RuleTreeNode.vue # 规则树节点
```

```
rules/                   # 分类规则目录
└── screwdriver-press-start/
    └── 按压启动.yaml     # 示例：小电动螺丝批按压启动分类规则
```

## 分类流程

```
专利文本
  │
  ▼
┌─────────────────────────────────────────────────┐
│  预处理                                          │
│  PatentParser → PatentSplitter                   │
│  提取：标题 / 摘要 / 权利要求 / 技术领域 / 背景   │
└─────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────┐
│  逐层递进分类 (ClassificationEngine)             │
│                                                  │
│  对每一层级：                                     │
│  ┌───────────────────────────────────────────┐   │
│  │ Layer1 粗分类 (RuleExtractor)             │   │
│  │ 关键词匹配 + 正则匹配 → 缩小候选范围       │   │
│  │ 排除命中排除关键词的分支                    │   │
│  └───────────────────────────────────────────┘   │
│    │                                              │
│    ▼                                              │
│  ┌───────────────────────────────────────────┐   │
│  │ Layer2 中分类 (LLM)                       │   │
│  │ 输入：摘要 + 权利要求1 + 候选分支判定标准   │   │
│  │ 输出：Top-2 候选 + 置信度                  │   │
│  └───────────────────────────────────────────┘   │
│    │                                              │
│    ▼ 置信度 < 阈值时触发                          │
│  ┌───────────────────────────────────────────┐   │
│  │ Layer3 细分类 (LLM)                       │   │
│  │ 输入：专利全文 + 详细判定标准 + 样本对比     │   │
│  │ 输出：最终分类 + 置信度 + 判定依据           │   │
│  └───────────────────────────────────────────┘   │
│                                                  │
│  选定当前层级分支 → 进入子分支 → 重复直到叶子节点  │
└─────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────┐
│  输出结果                                        │
│  完整路径：按压启动 > 单一按压启动 > 机械开关触发  │
│  置信度：综合取路径最低值                          │
│  需审核：置信度 < 阈值时标记                       │
└─────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+（仅 Web 界面需要）

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd patsona

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置

在项目根目录创建 `.env` 文件：

```env
# LLM 模型配置（三选一）
LITELLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com

# 或使用 DeepSeek
# LITELLM_MODEL=deepseek/deepseek-chat
# DEEPSEEK_API_KEY=sk-xxx

# 或使用智谱
# LITELLM_MODEL=zhipu/glm-4-flash
# ZHIPU_API_KEY=xxx

# 分类配置
RULES_DIR=rules
CONFIDENCE_THRESHOLD=0.6
```

### CLI 使用

```bash
# 直接分类粘贴的专利文本
patsona classify "一种电动螺丝批，包括壳体和电机..."

# 从文件分类
patsona classify-file patent.pdf

# 批量分类目录下的专利文件
patsona classify-batch ./patents/ -o results.md

# 指定模型
patsona classify "专利文本..." -m deepseek/deepseek-chat

# 校验分类规则
patsona check-rules

# 导入 Excel 样本
patsona import-samples samples.xlsx
```

### Web 界面

```bash
# 安装前端依赖
cd web/frontend
npm install

# 开发模式（分别启动后端和前端）
# 终端1：启动后端
cd web/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 终端2：启动前端
cd web/frontend
npm run dev

# 或使用 Windows 一键启动脚本
web\run.bat
```

访问 http://localhost:3000 使用 Web 界面。

API 文档：http://localhost:8000/docs

## 分类规则

分类规则以 YAML 文件定义，放在 `rules/` 目录下，支持子目录组织。

### 嵌套格式（推荐）

```yaml
tech_branch:
  id: "screwdriver-press-start"
  name: "小电动螺丝批-按压启动"
  level: 1

children:
  - id: "single-press"
    name: "单一按压启动"
    level: 2
    keywords:
      any_of: ["按压启动", "按压触发"]
      exclude: ["速度控制", "多级"]
    children:
      - id: "single-press-mechanical"
        name: "机械开关触发"
        level: 3
        criteria:
          - "权利要求中描述实体开关元件"
          - "按压行程末端触发开关"
        keywords: ["机械开关", "触点开关"]
```

### 列表格式

```yaml
branches:
  - id: "A01"
    name: "数据采集-传感器"
    parent_id: "A"
    keywords: ["传感器", "采集"]
    criteria: "涉及物理传感器的数据采集技术"
```

### 规则字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 分支唯一标识 |
| `name` | 是 | 分支名称 |
| `parent_id` | 否 | 父节点 ID，用于构建层级树 |
| `keywords` | 否 | 关键词列表，Layer1 用于快速匹配 |
| `patterns` | 否 | 正则模式列表，Layer1 用于模式匹配 |
| `exclude_keywords` | 否 | 排除关键词，命中则排除该分支 |
| `criteria` | 否 | 判定标准描述，Layer2/3 供 LLM 使用 |
| `detailed_criteria` | 否 | 详细判定标准，Layer3 使用 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/classify` | 单条文本分类 |
| POST | `/api/classify/batch` | 批量文本分类 |
| POST | `/api/classify/upload` | 上传文件分类 |
| GET | `/api/rules` | 获取规则树 |
| GET | `/api/rules/tree` | 获取规则树文本 |
| GET | `/api/config` | 获取当前配置 |
| POST | `/api/config` | 保存配置 |
| POST | `/api/upload/excel-info` | 获取 Excel 列信息 |
| POST | `/api/upload/excel-process` | 处理 Excel 数据 |
| POST | `/api/upload/file` | 上传文件并解析 |
| GET | `/health` | 健康检查 |

## 技术栈

**后端核心**
- Python 3.10+ / pydantic-settings / Typer / Rich
- httpx（LLM API 调用）/ pdfplumber / python-docx / openpyxl / PyYAML

**Web 服务**
- FastAPI / Uvicorn（后端）
- Vue 3 / Vite（前端）

## 项目依赖

```
patsona/
├── pydantic-settings    配置管理
├── typer + rich         CLI 界面
├── httpx                HTTP 客户端（LLM 调用）
├── pdfplumber           PDF 解析
├── python-docx          DOCX 解析
├── openpyxl             Excel 读写
├── pyyaml               YAML 规则加载

web/backend/
├── fastapi              Web 框架
├── uvicorn              ASGI 服务器
├── python-multipart     文件上传

web/frontend/
├── vue 3                前端框架
├── vite                 构建工具
```
