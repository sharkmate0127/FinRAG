# FinRAG — 金融研报智能问答系统

基于 RAG（检索增强生成）+ Agent 的金融研报智能问答系统。
用户上传金融研报 PDF 后，可针对内容进行智能问答，支持数值推理与引用溯源，
并能调用工具查询实时股价与财务数据。

## 核心特性

- **智能问答**：基于检索内容的精准回答，从根本上抑制大模型幻觉
- **引用溯源**：每条答案标注来源研报与段落，可解释、可验证
- **Agent 工具调用**：实时股价（akshare）+ 财务数据（tushare）
- **双模式架构**：云端 API（开发）+ 本地 Ollama INT4（部署）

## 技术栈

| 类别 | 选型 |
|---|---|
| 语言 | Python 3.11 |
| 大模型 | DeepSeek / Qwen2.5-7B-Instruct（双模式） |
| 框架 | LangChain 0.3+（LCEL 语法） |
| 向量库 | ChromaDB（开发中） |
| Embedding | bge-large-zh-v1.5（开发中） |
| Reranker | bge-reranker-large（开发中） |
| Agent | LangChain Tool Calling（开发中） |
| 数据接口 | akshare / tushare（开发中） |
| 前端 | Gradio |
| 后端 | FastAPI（开发中） |
| 评估 | RAGAS（开发中） |
| 部署 | Docker（开发中） |

## 当前进展
![第一周界面](docs/week1-screenshot.png)


### ✅ 已完成（第1 周）

- **Day 1-2**：项目边界 / 系统架构图 / 技术栈 / 算力方案- **Day 3-4**：环境搭建（Python 3.11 + venv + Gradio Hello World 跑通）

![界面截图](docsscreenshot-day3-4.png)
- **Day 5**：模型接入（DeepSeek API +第一个 LangChain Chain 跑通）


## 知识库

- **21 份券商深度研报**，覆盖 11 家上市公司、4 大赛道：
  - 新能源车链：宁德时代、比亚迪、拓普集团、亿纬锂能
  - 光伏储能：阳光电源、隆基绿能
  - AI 算力：浪潮信息、中科曙光、工业富联
  - AI 应用：科大讯飞、金山办公
- **1323 个知识块**（500-1000 字符/块，带来源元数据）

## 当前进展

### ✅ 已完成（第 1-3 周）

| 阶段 | 内容 | 状态 |
|---|---|---|
| Day 1-5 | 项目规划 / 环境搭建 / DeepSeek 模型接入 | ✅ |
| Day 6-10 | 数据采集（21 份研报）/ 分块（1323块）/ 向量化入库 | ✅ |
| Day 11-12 | RAG 核心管线 v0.1（检索+上下文+生成） | ✅ |
| Day 13-14 | Prompt 工程 A/B 测试，ask.py v0.2 | ✅ |
| Day 15 | 引用溯源增强 v0.3（编号引用+验证脚本） | ✅ |
- 数值推理（Day 16-17）：10 题评测集准确率 **70%**（Few-Shot + 表格引导）

### 🚧 开发中


### 📅 待办
- W4：Agent 工具调用 + 混合检索优化
- W5：RAGAS 评估 + 双模式对比 + 部署
- W6：论文 + 面试准备

## 评估结果（A/B 测试，2026-08-15）

4 版 Prompt × 12 题（0-3 分人工评分）：

| 版本 | 设计 | 平均分 |
|---|---|---|
| P0 | 极简 baseline | 1.75 |
| P1 | 角色 + 防幻觉约束 | 2.30 |
| P2 | P1 + 数值标注 | 2.40 |
| **P3** | P2 + 综合分析引导 | **2.60** ✅ |
- 检索对比实验（Day 18）：单一向量 / 混合 /混合+重排 三种方案 Hit Rate 均 **100%**


> 结论：Prompt 结构化设计将回答质量提升 **48.6%**（P3 vs P0）。

## 快速开始

### 环境要求
- Python 3.10+（推荐 3.11）
- Windows / macOS / Linux

### 安装

```bash
git clone https://github.com/sharkmate0127/FinRAG.git
cd FinRAG
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### 配置

创建 `.env` 文件（DeepSeek 平台申请 Key）：

```
DEEPSEEK_API_KEY=sk-你的Key
```

国内访问 HuggingFace 需设置镜像（每个新终端执行）：

```bash
# PowerShell:
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

### 数据准备（一次性的）

```bash
# 1. 解析 PDF（需先放入 data/raw/）
python parse_pdfs.py

# 2. 分块
python chunk_texts.py

# 3. 向量化入库（首次下载 bge 模型约 1.3GB）
python build_vector_db.py
```

### 运行

```bash
# RAG 问答（交互式，带引用溯源）
python ask.py

# 检索质量测试
python query_test.py

# Prompt A/B 测试
python ab_test.py

# 引用准确率验证
python check_citations.py

# Gradio 界面（Hello World）
python app_gradio.py
```

## 项目结构

```
FinRAG/
├── ask.py                 # RAG 问答主程序（v0.3 编号引用版）
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
├── data/
│   ├── raw/               # 原始 PDF（不入库）
│   ├── parsed/            # 解析文本
│   ├── chunks/            # 知识块（jsonl）
│   ├── vector_db/         # 向量库（不入库）
│   └── abtest/            # 实验数据
└── README.md
```


## 6 周里程碑

| 周 | 主题 | 状态 |
|---|---|---|
| W1 | 项目启动 + 环境搭建 | ✅ |
| W2 | 数据工程与知识库 | 🚧 |
| W3 | RAG 核心管线 | 📅 |
| W4 | Agent + 检索优化 | 📅 |
| W5 | 评估 + 部署 | 📅 |
| W6 | 论文 + 面试 | 📅 |

## License

MIT

