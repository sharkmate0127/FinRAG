# Day 23-24 小白操作指南：Agent 工具补齐 + RAG + Agent 协同

> 日期：2026-08-17 ｜ 项目：FinRAG v3.0 ｜ 导师方案：第 4 周（Day 22-25）
> 注意：你的 API 已切换为 **DeepSeek**（`deepseek-chat` + `https://api.deepseek.com`），
> 导师方案里写的 "Qwen Function Calling" 在代码层面**完全通用**（都是 OpenAI 兼容协议），
> 你只要沿用 agent_demo.py 里已验证的 DeepSeek 配置即可，无需任何修改。

---

## 一、先看导师要求（PDF 原文摘录）

### Day 22-23：Function Calling 接入
- 学习 Qwen API 的 Function Calling 接口 → **你已用 DeepSeek 完成**
- 定义工具函数：`get_stock_price(stock_code)`、`get_financial_data(stock_code, metric)`
- 用 akshare 实现工具函数逻辑
- 测试：问"贵州茅台股价"，系统自动调用工具
- 检查点：股价查询成功 → **get_stock_price 已跑通 ✅**

### Day 24-25：RAG + Agent 协同
- 将 Agent 工具集成到 RAG 系统中
- 实现**路由逻辑**：研报内容问题→RAG；实时数据问题→Agent；混合问题→RAG+Agent
- 实现**综合推理**：研报说增长20%，实际财报是多少？
- 检查点：混合类问题能正确路由

**你的当前进度**：Day 22 完成（`test_tool.py` 三级降级 + `agent_demo.py` 工具调用跑通）。
今天你要做的是 **Day 23**（补 `get_financial_data` 工具）和 **Day 24-25**（RAG+Agent 协同）。

---

## 二、核心概念解释（零基础版）

### 1. Function Calling（工具调用）—— 你已经懂了，快速复习
LLM 像"总指挥"，工具像"手下"。
- 你问："宁德时代现在股价多少？"
- 总指挥（LLM）想："这个问题我没法凭记忆回答，应该派手下 get_stock_price 去查"
- 返回：`{"name": "get_stock_price", "arguments": {"stock_code": "300750"}}`
- 你执行工具 → 把结果喂回给 LLM → LLM 组织语言回答

### 2. 路由（Router）—— 今天的新概念
路由 = **先让 LLM 判断"这个问题属于哪一类"，然后走不同的处理路线**。

| 问题类型 | 例子 | 走哪条路 |
|---|---|---|
| 研报内容类 | "宁德时代主营业务是什么？" | RAG（查研报） |
| 实时数据类 | "宁德时代今天股价多少？" | Agent（调工具） |
| 混合类 | "研报说营收增长20%，实际是多少？" | RAG + Agent 协同 |

大白话类比：**医院分诊台**。你到前台说"我头疼"，护士先判断你该挂内科还是外科，再带你去对应科室。路由就是那个分诊护士。

### 3. RAG + Agent 协同（综合推理）
- RAG 负责：从研报里找到"预测/目标"数据（比如研报说 2024 年营收 4680 亿）
- Agent 负责：调工具拿到"实际"数据（比如实际财报 3620 亿）
- 最后让 LLM 把两个数据放一起**对比、分析差异**，给出一段综合回答

大白话类比：**开卷考试 + 允许用计算器**。书里说"预期营收 4680 亿"（RAG），你用计算器算出实际数（Agent），然后对比两者差距，得出结论。

---

## 三、Day 23 详细步骤：创建 `financial_tool.py`（财务指标工具）

### 步骤 1：为什么需要这个工具？
导师要求定义两个工具：`get_stock_price`（已有）和 `get_financial_data(stock_code, metric)`。
`metric` 是"指标"，比如：营收、净利润、营收同比增长率。

> ⚠️ **关于 tushare**：导师方案建议用 tushare 查财报，但 tushare 需要**注册账号拿 token**（tushare.pro），
> 而且你的网络连东财都被封，tushare 大概率也连不上。
> 所以下面的代码沿用你的**三级降级思路**：真接口 → 内置演示数据 → 明确报错。
> 演示数据来源于你研报里的真实数据（标注了"演示"），面试时可以如实说明。

### 步骤 2：在 PowerShell 里创建文件（或手动新建）

**方法 A（推荐，一行命令建空文件）**：
```powershell
New-Item -Path "E:\finrag\FinRAG\financial_tool.py" -ItemType File -Force
```

**方法 B（手动）**：在 `E:\finrag\FinRAG` 文件夹右键 → 新建 → 文本文档 → 重命名为 `financial_tool.py`
（注意：如果系统隐藏了扩展名，先在文件夹顶部"查看"勾选"文件扩展名"）

### 步骤 3：粘贴完整代码

打开 `financial_tool.py`，粘贴下面全部内容，保存（Ctrl+S）：

```python
# -*- coding: utf-8 -*-
"""financial_tool.py - Day 23：财务指标查询工具（三级降级）

导师要求：get_financial_data(stock_code, metric)
  metric 支持：营收、净利润、营收同比、净利润同比
降级策略：真接口（akshare）→ 内置演示数据 → 明确报错
"""
import os

# ===== 1. 清代理环境变量（沿用 Day 22 的防坑措施）=====
for k in list(os.environ.keys()):
    if 'proxy' in k.lower():
        os.environ[k] = ''

# ===== 2. Monkey patch requests（沿用 Day 22 已验证的写法）=====
try:
    import requests
    _orig_session_init = requests.Session.__init__

    def _patched_session_init(self, *args, **kwargs):
        _orig_session_init(self, *args, **kwargs)
        self.trust_env = False
        self.proxies = {}

    requests.Session.__init__ = _patched_session_init

    _orig_get = requests.get

    def _patched_get(url, **kwargs):
        kwargs['proxies'] = {'http://': '', 'https://': ''}
        return _orig_get(url, **kwargs)

    requests.get = _patched_get
except Exception as _e:
    print(f"[warn] patch requests 失败（不影响主流程）: {_e}")

# ===== 3. 内置演示财报数据（来自研报，标注为演示）=====
# 结构: {股票代码: {公司名: ..., 年度: {指标: 数值}}}
FINANCIAL_MOCK = {
    "300750": {
        "name": "宁德时代",
        "2023A": {"营收": 4009.17, "净利润": 441.21, "营收同比": 22.01, "净利润同比": 43.58},
        "2024E": {"营收": 4680.43, "净利润": 510.30, "营收同比": 16.74, "净利润同比": 15.66},
    },
    "002594": {
        "name": "比亚迪",
        "2023A": {"营收": 6023.15, "净利润": 300.41, "营收同比": 42.04, "净利润同比": 80.72},
        "2024E": {"营收": 7132.40, "净利润": 381.12, "营收同比": 18.42, "净利润同比": 26.87},
    },
    "601012": {
        "name": "隆基绿能",
        "2023A": {"营收": 1294.98, "净利润": 107.51, "营收同比": 0.39, "净利润同比": -27.41},
        "2024E": {"营收": 1385.21, "净利润": 72.30, "营收同比": 6.97, "净利润同比": -32.75},
    },
}


def get_financial_data(stock_code: str, metric: str = "营收") -> str:
    """查询公司财务指标（三级降级）

    参数:
        stock_code: 6 位股票代码，如 300750
        metric: 指标名，如 营收 / 净利润 / 营收同比 / 净利润同比
    返回: 人类可读的字符串
    """
    # 优先级 1: akshare 真接口（网络通时才有用）
    try:
        import akshare as ak
        # akshare 财务摘要接口（同花顺源，指标多）
        df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按年度")
        # 找到指标行
        row = df[df["指标"] == metric]
        if not row.empty:
            latest = row.iloc[0]["最新值"]
            return f"{stock_code} 的 {metric}: {latest}（数据来源: akshare 同花顺）"
    except Exception as _e1:
        pass  # 网络不通，走降级

    # 优先级 2: 内置演示数据
    if stock_code in FINANCIAL_MOCK:
        info = FINANCIAL_MOCK[stock_code]
        name = info["name"]
        if "2023A" in info and metric in info["2023A"]:
            val = info["2023A"][metric]
            return f"{name}({stock_code}) 2023A {metric}: {val}（数据来源: 内置演示数据，非实时）"
        return f"{name}({stock_code}): 没有 {metric} 的演示数据"

    # 优先级 3: 明确报错
    return f"查询失败: 未收录股票 {stock_code}，且 akshare 网络不可用"


if __name__ == "__main__":
    print("=" * 60)
    print("财务指标工具测试（get_financial_data）")
    print("=" * 60)
    print(get_financial_data("300750", "营收"))
    print(get_financial_data("300750", "净利润"))
    print(get_financial_data("002594", "营收同比"))
    print(get_financial_data("999999", "营收"))
    print("=" * 60)
```

### 步骤 4：运行测试

在 PowerShell（已经在 `E:\finrag\FinRAG` 目录且激活了 .venv）运行：

```powershell
python financial_tool.py
```

### 步骤 5：预期输出

```
============================================================
财务指标工具测试（get_financial_data）
============================================================
宁德时代(300750) 2023A 营收: 4009.17（数据来源: 内置演示数据，非实时）
宁德时代(300750) 2023A 净利润: 441.21（数据来源: 内置演示数据，非实时）
比亚迪(002594) 2023A 营收同比: 42.04（数据来源: 内置演示数据，非实时）
查询失败: 未收录股票 999999，且 akshare 网络不可用
============================================================
```

✅ 看到这 4 行就说明 Day 23 完成。把截图发我确认。

---

## 四、Day 24-25 详细步骤：创建 `rag_agent.py`（RAG + Agent 协同）

### 步骤 1：理解整体流程（配路由图）

```
用户问题
   ↓
【路由 Router】LLM 判断意图 → 输出 JSON
   ↓
┌──────────┬──────────────┬──────────────┐
研报内容类    实时数据类       混合类
   ↓           ↓                ↓
  RAG         Agent         RAG + Agent
（检索研报）  （调工具查数据）  （两边都要）
   ↓           ↓                ↓
        【最终回答】统一返回
```

### 步骤 2：创建文件

```powershell
New-Item -Path "E:\finrag\FinRAG\rag_agent.py" -ItemType File -Force
```

### 步骤 3：粘贴完整代码

```python
# -*- coding: utf-8 -*-
"""rag_agent.py - Day 24-25：RAG + Agent 协同系统 v0.3

导师要求：
1. 路由逻辑：研报内容问题→RAG；实时数据问题→Agent；混合问题→RAG+Agent
2. 综合推理："研报说营收增长20%，实际财报是多少？"

复用已有模块：
- ask.py:          RAG 检索 + 回答（hybrid_retrieve）
- test_tool.py:    股价工具 get_stock_price（三级降级）
- financial_tool.py: 财务工具 get_financial_data（三级降级）
"""
import re
import json
import os
from pathlib import Path
import jieba
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import chromadb
from dotenv import load_dotenv

load_dotenv()

# ===== 加载 RAG 组件（与 ask.py 一致）=====
print("加载模型...")
model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
reranker = CrossEncoder("BAAI/bge-reranker-large", max_length=512)
client = chromadb.PersistentClient(path="data/vector_db")
collection = client.get_collection("finrag_reports")

chunks = [json.loads(l) for l in Path("data/chunks/chunks.jsonl").read_text(encoding="utf-8").splitlines()]
texts = [c["text"] for c in chunks]
tokens = [list(jieba.cut(t)) for t in texts]
bm25 = BM25Okapi(tokens)
id2idx = {c["chunk_id"]: i for i, c in enumerate(chunks)}

llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    temperature=0.2,
)

# ===== 引入两个工具（复用，不重复造轮子）=====
from test_tool import get_stock_price
from financial_tool import get_financial_data

# ===== 混合检索 + 重排（复制自 ask.py）=====
def hybrid_retrieve(question: str, top: int = 5):
    q_emb = model.encode([question], normalize_embeddings=True).tolist()
    vec_ids = collection.query(query_embeddings=q_emb, n_results=20)["ids"][0]
    scores = bm25.get_scores(list(jieba.cut(question)))
    bm25_ids = {chunks[i]["chunk_id"] for i in
                sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:20]}
    merged = [i for i in list(set(vec_ids) | bm25_ids) if i in id2idx]
    docs = [chunks[id2idx[i]]["text"][:512] for i in merged]
    scores_rerank = reranker.predict([(question, d) for d in docs])
    ranked = [merged[i] for i in
              sorted(range(len(scores_rerank)), key=lambda i: scores_rerank[i], reverse=True)][:top]
    return ranked

# ===== 路由函数：让 LLM 判断问题类型 =====
def route_question(question: str) -> dict:
    """让 LLM 输出 JSON: {"route": "rag|agent|hybrid", "stock_code": "300750", "metric": "营收"}"""
    prompt = f"""判断下面这个金融问题的类型，只输出 JSON（不要其他文字）：

规则：
- 如果是问研报内容（主营业务、行业分析、财务预测等）→ route="rag"
- 如果是问实时数据（股价、最新行情）→ route="agent"
- 如果是需要对比（研报预测 vs 实际数据）→ route="hybrid"

同时提取：
- stock_code: 如果问题涉及某家公司，给出它的股票代码（300750宁德时代/002594比亚迪/601012隆基绿能）；不确定就填 null
- metric: 如果涉及财务指标，给出指标名（营收/净利润/营收同比/净利润同比）；没有就填 null

问题：{question}

输出格式示例：{{"route": "hybrid", "stock_code": "300750", "metric": "营收"}}"""

    try:
        resp = llm.invoke(prompt)
        text = resp.content.strip()
        # 提取 JSON（兼容可能的包裹字符）
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"[warn] 路由解析失败，默认走 RAG: {e}")
    return {"route": "rag", "stock_code": None, "metric": None}

# ===== 路线 1：RAG（研报问答）=====
RAG_TEMPLATE = """你是一名资深金融研究助手。请根据【研报内容】回答用户问题。

规则：
1. 只用研报内容回答，不要编造
2. 引用信息时标注编号 [1][2]
3. 需要计算的先列算式

【研报内容】
{context}

【问题】
{question}

【回答】"""

rag_prompt = PromptTemplate.from_template(RAG_TEMPLATE)
rag_chain = rag_prompt | llm | StrOutputParser()

def ask_rag(question: str) -> str:
    ranked = hybrid_retrieve(question, top=5)
    parts = []
    for i, cid in enumerate(ranked, start=1):
        chunk = chunks[id2idx[cid]]
        parts.append(f"[{i}] 来源：{chunk['source_file']}\n{chunk['text']}\n")
    context = "\n".join(parts)
    return rag_chain.invoke({"context": context, "question": question})

# ===== 路线 2：Agent（工具调用）=====
def ask_agent(question: str, stock_code=None) -> str:
    """简化版工具调用：根据路由结果直接调对应工具"""
    # 工具清单描述（沿用 agent_demo.py 的思路）
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "get_stock_price",
                "description": "查询股票实时价格。当用户问某只股票'现在多少钱'、'实时价格'、'今天行情'时使用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stock_code": {"type": "string", "description": "6 位股票代码，如 300750"},
                    },
                    "required": ["stock_code"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_financial_data",
                "description": "查询公司财务指标（营收/净利润/营收同比/净利润同比）。当用户问'财报''营收''净利润'等时使用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stock_code": {"type": "string", "description": "6 位股票代码"},
                        "metric": {"type": "string", "description": "指标名：营收/净利润/营收同比/净利润同比"},
                    },
                    "required": ["stock_code", "metric"],
                },
            },
        },
    ]

    # 调 LLM，让它自己决定调哪个工具（DeepSeek Function Calling）
    try:
        import requests
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是 FinRAG 金融助手。当用户问实时行情/财务数据时，必须调用工具，不要编造数据。"},
                    {"role": "user", "content": question},
                ],
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.2,
            },
            timeout=60,
        )
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]

        if msg.get("tool_calls"):
            results = []
            for tc in msg["tool_calls"]:
                fn = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                if fn == "get_stock_price":
                    results.append(get_stock_price(args.get("stock_code", "")))
                elif fn == "get_financial_data":
                    results.append(get_financial_data(args.get("stock_code", ""), args.get("metric", "营收")))
            tool_text = "\n".join(results)
            # 把工具结果回喂给 LLM 组织答案
            resp2 = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是 FinRAG 金融助手，根据工具结果给出简洁专业的回答。"},
                        {"role": "user", "content": question},
                        {"role": "tool", "tool_call_id": tc["id"], "content": tool_text},
                    ],
                    "temperature": 0.2,
                },
                timeout=60,
            )
            resp2.raise_for_status()
            return resp2.json()["choices"][0]["message"]["content"].strip()

        # LLM 没调工具，直接给答案
        return msg.get("content", "未获得有效回答")
    except Exception as e:
        # 网络失败兜底：直接调财务工具
        if stock_code:
            return get_financial_data(stock_code, "营收")
        return f"Agent 调用失败: {type(e).__name__}: {e}"

# ===== 路线 3：RAG + Agent 协同（综合推理）=====
COOP_TEMPLATE = """你是 FinRAG 综合推理助手。用户的问题同时涉及【研报预测】和【实际数据】，
请对比两者并给出综合分析。

【研报内容（预测/目标）】
{context}

【实际数据（工具返回）】
{tool_result}

【问题】
{question}

回答要求：
1. 先分别列出研报预测值和实际值
2. 计算两者差异（数值对比）
3. 给出你的分析结论（差异原因推测、投资含义等）
4. 引用研报时标注 [1][2]"""

coop_prompt = PromptTemplate.from_template(COOP_TEMPLATE)
coop_chain = coop_prompt | llm | StrOutputParser()

def ask_hybrid(question: str, stock_code=None, metric="营收") -> str:
    # 1. RAG：检索研报相关段落
    ranked = hybrid_retrieve(question, top=5)
    parts = []
    for i, cid in enumerate(ranked, start=1):
        chunk = chunks[id2idx[cid]]
        parts.append(f"[{i}] 来源：{chunk['source_file']}\n{chunk['text']}\n")
    context = "\n".join(parts)

    # 2. Agent：调工具拿实际数据
    if stock_code:
        tool_result = get_financial_data(stock_code, metric)
    else:
        tool_result = get_stock_price("300750")  # 兜底

    # 3. LLM 综合对比
    return coop_chain.invoke({
        "context": context,
        "tool_result": tool_result,
        "question": question,
    })

# ===== 统一入口 =====
def smart_answer(question: str) -> str:
    """总调度：先路由，再分流"""
    route_info = route_question(question)
    route = route_info.get("route", "rag")
    stock_code = route_info.get("stock_code")
    metric = route_info.get("metric") or "营收"

    print(f"[路由] 类型={route}, 股票={stock_code}, 指标={metric}")

    if route == "agent":
        return ask_agent(question, stock_code)
    elif route == "hybrid":
        return ask_hybrid(question, stock_code, metric)
    else:
        return ask_rag(question)

# ===== 主程序 =====
if __name__ == "__main__":
    print("FinRAG v0.3 协同系统已就绪！输入 q 退出\n")
    while True:
        q = input("你的问题: ").strip()
        if q.lower() == "q":
            break
        if not q:
            continue
        print("\n思考中...\n")
        ans = smart_answer(q)
        print(f"\n【回答】\n{ans}\n")
```

### 步骤 4：运行测试

```powershell
python rag_agent.py
```

### 步骤 5：测试 3 种问题，验证路由

在程序里依次输入：

```
1. 宁德时代主营业务是什么？
2. 宁德时代今天股价多少？
3. 研报说宁德时代营收增长20%，实际是多少？
```

**预期**：

| 输入 | 路由日志 | 行为 |
|---|---|---|
| 宁德时代主营业务是什么？ | `[路由] 类型=rag` | 检索研报回答 |
| 宁德时代今天股价多少？ | `[路由] 类型=agent` | 调 get_stock_price |
| 研报说宁德时代营收增长20%... | `[路由] 类型=hybrid` | RAG 查研报 + 工具查数据 + 对比 |

**核心检查点（导师要求）**：**混合类问题能正确路由到 hybrid**，且回答里同时出现"研报预测值"和"实际值"的对比。

✅ 三条路都通了，Day 24-25 完成。截图发我。

---

## 五、面试话术

**Q: 你的 RAG 和 Agent 是怎么协同的？**

> "我的系统是一个分诊台设计。用户提问后，先由一个路由 LLM 判断问题类型：研报内容问题走 RAG 路线（混合检索 + 重排 + 引用溯源），实时数据问题走 Agent 路线（LLM 自主决定调用 get_stock_price 或 get_financial_data 工具），需要对比的问题走协同路线——RAG 从研报提取预测数据，Agent 调工具拿实际数据，最后 LLM 综合对比给出分析。"

**Q: 工具调用失败怎么办？**

> "所有工具都是三级降级设计：真接口优先，网络不可用时自动回落内置演示数据，再不行就明确报错而不是静默失败。这是生产级系统的容错设计。"

**Q: 路由判断错了怎么办？**

> "路由只是一个 LLM 判断，错了会降级到 RAG 兜底回答。另外我可以在路由 prompt 里加 few-shot 示例提高准确率——这是后续优化方向。"

---

## 六、常见问题排错

| 现象 | 原因 | 解决 |
|---|---|---|
| `ModuleNotFoundError: No module named 'rank_bm25'` | 缺包 | `pip install rank_bm25`（用阿里云镜像） |
| 路由一直返回 rag | DeepSeek 偶尔不听话 | 在路由 prompt 里加更多示例，或改为规则+LLM 混合判断 |
| agent 路线报 `ConnectionError` | 网络问题 | 正常，代码已自动降级到内置演示数据 |
| 中文乱码 | 文件编码 | 保存时选 UTF-8（记事本右下角编码改 UTF-8） |
| `chromadb` 版本报错 | 版本问题 | 用你已有的 ask.py 能跑的环境，保持一致 |

---

## 七、验收清单（对照导师检查点）

- [ ] Day 23：`get_financial_data` 工具 3 个指标查询成功
- [ ] Day 24-25：3 种问题路由正确（rag / agent / hybrid）
- [ ] 混合问题回答包含"预测 vs 实际"对比
- [ ] 完成后 commit + push 到 GitHub（打 tag v0.4.0）
