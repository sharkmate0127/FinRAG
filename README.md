# FinRAG — 金融研报智能问答系统

基于 **RAG（检索增强生成）+ Agent（工具调用）** 双架构的金融研报智能问答系统。
用户上传金融研报 PDF 后，可针对内容进行智能问答，支持数值推理与引用溯源，
并能调用工具查询实时股价与财务数据，实现"研报预测 vs 实际数据"综合对比。

> 项目定位：一个项目打穿 RAG + Agent + 量化评估 + 工程部署全链路（6 周冲刺，已完成 W1-W4）。

## 核心特性

- **智能问答**：基于检索内容的精准回答，从根本上抑制大模型幻觉
- **引用溯源**：每条答案标注来源研报与段落编号，可解释、可验证
- **数值推理**：Few-Shot 引导，财务表格数据自动提取与计算
- **Agent 工具调用**：LLM 自主决定调 `get_stock_price` / `get_financial_data`
- **RAG + Agent 协同**：路由分诊——研报问题走 RAG，实时问题走 Agent，混合问题两边协同对比
- **多轮对话**：滑动窗口记忆 + 追问增强（"那毛利率呢"自动接上文）
- **三级降级**：真接口 → 本地演示数据 → 明确报错（网络不可用不崩溃）

## 技术栈

| 类别 | 选型 | 状态 |
|---|---|---|
| 语言 | Python 3.11 | ✅ |
| 大模型 | DeepSeek（deepseek-chat API） | ✅ |
| 框架 | LangChain 0.3+（LCEL 语法） | ✅ |
| 向量库 | ChromaDB | ✅ |
| Embedding | bge-large-zh-v1.5（1024 维） | ✅ |
| Reranker | bge-reranker-large（二次排序） | ✅ |
| Agent | DeepSeek Function Calling（OpenAI 兼容协议） | ✅ |
| 数据接口 | akshare（股价/财务，三级降级） | ✅ |
| 前端 | Gradio | 🚧（周 5 升级） |
| 后端 | FastAPI | 📅（周 5） |
| 评估 | RAGAS | 📅（周 5） |
| 部署 | Docker | 📅（周 5） |

## 当前进展

### ✅ 已完成（第 1-4 周）

| 阶段 | 内容 | 关键结果 |
|---|---|---|
| Day 1-5 | 项目规划 / 环境搭建 / DeepSeek 接入 | 环境跑通 |
| Day 6-10 | 数据采集（21 份研报）/ 分块（1323 块）/ 向量化入库 | 知识库建成 |
| Day 11-12 | RAG 核心管线 v0.1（检索+上下文+生成） | 端到端跑通 |
| Day 13-14 | Prompt 工程 A/B 测试，ask.py v0.2 | P3 胜出 |
| Day 15 | 引用溯源增强 v0.3 | 编号引用+验证 |
| Day 16-17 | 数值推理增强（Few-Shot）v0.4 | 评测集准确率 **70%** |
| Day 18 | 检索质量优化 v0.5 | Hit Rate **100%**，混合+重排 MRR **1.000** |
| Day 19-20 | 多轮对话 v0.6 + 端到端测试 | 8-9/9 通过 |
| Day 21-22 | Agent 工具调用（股价查询） | LLM 自主调工具 ✅ |
| Day 23-24 | RAG + Agent 协同 v0.4 | 路由 + 综合推理跑通 |
| Day 25 | 协同版检索验证 + 路由准确率 | Hit Rate **100%**，路由准确率 **100%** |
| Day 26 | 协同版多轮对话 + 异常处理 + 端到端测试 | 5 轮追问不跑题 |

### 🚧 开发中（第 5 周）
- RAGAS 评估（Faithfulness / Answer Relevancy / Context Precision / Context Recall）
- 双模式对比（API vs 本地 Ollama INT4）
- FastAPI 后端 + Docker 部署 + Gradio 界面升级

### 📅 待办（第 6 周）
- 论文撰写 + GitHub 仓库优化 + 面试准备

## 评估结果

### Prompt A/B 测试（2026-08-15）

4 版 Prompt × 12 题（0-3 分人工评分）：

| 版本 | 设计 | 平均分 |
|---|---|---|
| P0 | 极简 baseline | 1.75 |
| P1 | 角色 + 防幻觉约束 | 2.30 |
| P2 | P1 + 数值标注 | 2.40 |
| **P3** | P2 + 综合分析引导 | **2.60** ✅ |

> 结论：Prompt 结构化设计将回答质量提升 **48.6%**（P3 vs P0）。

### 检索质量实验（Day 18）

- 单一向量 / 混合 / 混合+重排 三种方案 Hit Rate 均 **100%**
- 精排对比：混合+BM25 MRR 0.85（BM25 引入噪音）→ 加 Reranker 后回到 **1.000**
- 最终采用：**混合检索 + 重排**方案

### 协同版验证（Day 25）

- 协同版检索 Hit Rate：**100% (10/10)**（含混合类问题）
- 路由准确率：**100% (10/10)**（rag / agent / hybrid 三类意图判断全对）

## 知识库

- **21 份券商深度研报**，覆盖 11 家上市公司、4 大赛道：
  - 新能源车链：宁德时代、比亚迪、拓普集团
  - 光伏储能：阳光电源、隆基绿能
  - AI 算力：浪潮信息、中科曙光、工业富联
  - AI 应用：科大讯飞、金山办公
- **1323 个知识块**（500-1000 字符/块，带来源与股票代码元数据）

## 快速开始

### 环境要求
- Python 3.10+（推荐 3.11）
- Windows / macOS / Linux

### 安装

git clone https://github.com/sharkmate0127/FinRAG.git
cd FinRAG
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

### 配置

创建 `.env` 文件（DeepSeek 平台申请 Key）：

DEEPSEEK_API_KEY=sk-你的Key

国内访问 HuggingFace 需设置镜像（每个新终端执行）：

# PowerShell:
$env:HF_ENDPOINT = "https://hf-mirror.com"

# 永久生效（执行一次，重启 PowerShell 后免设）：
# [Environment]::SetEnvironmentVariable("HF_ENDPOINT", "https://hf-mirror.com", "User")

### 数据准备（一次性的）

# 1. 解析 PDF（需先放入 data/raw/）
python parse_pdfs.py

# 2. 分块
python chunk_texts.py

# 3. 向量化入库（首次下载 bge 模型约 1.3GB）
python build_vector_db.py

### 运行

# RAG 问答（交互式，带引用溯源 + 多轮对话）
python ask.py

# RAG + Agent 协同系统（路由分诊：rag/agent/hybrid）
python rag_agent.py

# Agent 工具调用演示（LLM 自主决定调股价工具）
python agent_demo.py

# 股价工具测试（三级降级：akshare → 本地演示 → 报错）
python test_tool.py

# 财务指标工具测试
python financial_tool.py

# 协同版检索 + 路由验证
python eval_agent.py

# 协同版端到端测试
python e2e_agent_test.py

# 检索质量测试
python query_test.py

# Prompt A/B 测试
python ab_test.py

# 引用准确率验证
python check_citations.py

# Gradio 界面
python app_gradio.py

## 项目结构

FinRAG/
├── ask.py                 # RAG 问答主程序（多轮对话版 v0.6）
├── rag_agent.py           # RAG+Agent 协同系统（路由+工具调用+多轮对话）
├── agent_demo.py          # Agent 工具调用演示（Function Calling）
├── test_tool.py           # 股价工具（三级降级）
├── financial_tool.py      # 财务指标工具（三级降级）
├── eval_agent.py          # 协同版检索+路由验证
├── e2e_agent_test.py      # 协同版端到端测试
├── ab_test.py             # Prompt A/B 测试脚本
├── check_citations.py     # 引用准确率验证脚本
├── build_vector_db.py     # 向量化入库脚本
├── query_test.py          # 检索质量测试
├── chunk_texts.py         # 文本分块脚本
├── parse_pdfs.py          # PDF 批量解析
├── check_pdf.py           # PDF 质量检查
├── call_qwen.py           # LLM 调用测试
├── chain_demo.py          # LangChain Chain 示例
├── test_langchain.py      # LangChain 环境验证
├── app_gradio.py          # Gradio 界面
├── requirements.txt       # 依赖清单
├── .env                   # API Key（不入库）
├── docs/                  # 每阶段操作指南与沉淀文档
├── data/
│   ├── raw/               # 原始 PDF（不入库）
│   ├── parsed/            # 解析文本
│   ├── chunks/            # 知识块（jsonl）
│   ├── vector_db/         # 向量库（不入库）
│   ├── abtest/            # 实验数据
│   └── eval/              # 评测结果
└── README.md

## 6 周里程碑

| 周 | 主题 | 状态 |
|---|---|---|
| W1 | 项目启动 + 环境搭建 | ✅ |
| W2 | 数据工程与知识库 | ✅ |
| W3 | RAG 核心管线 | ✅ |
| W4 | Agent + 检索优化 + 协同 | ✅ |
| W5 | 评估 + 部署 | 🚧 |
| W6 | 论文 + 面试 | 📅 |

## License

MIT


