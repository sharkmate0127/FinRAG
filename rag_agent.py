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
def route_question(question: str, history=None) -> dict:
    """让 LLM 输出 JSON: {"route": "rag|agent|hybrid", "stock_code": "300750", "metric": "营收"}
    增加 history 参数：让路由能结合上文判断（如追问"那股价呢"）
    """
    history = history or []
    hist_text = format_history(history)
    prompt = f"""判断下面这个金融问题的类型，只输出 JSON（不要其他文字）：

规则：
- 如果是问研报内容（主营业务、行业分析、财务预测等）→ route="rag"
- 如果是问实时数据（股价、最新行情）→ route="agent"
- 如果是需要对比（研报预测 vs 实际数据）→ route="hybrid"

同时提取：
- stock_code: 如果问题涉及某家公司，给出它的股票代码（300750宁德时代/002594比亚迪/601012隆基绿能）；不确定就填 null
- metric: 如果涉及财务指标，给出指标名（营收/净利润/营收同比/净利润同比）；没有就填 null

【对话历史】（若问题是追问，可结合上文确定公司）
{hist_text}

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
# ===== 对话历史管理（滑动窗口：最多保留 5 轮）=====
history = []  # [(user, assistant), ...]

def format_history(history):
    if not history:
        return "（无历史对话）"
    lines = []
    for u, a in history[-5:]:
        lines.append(f"用户：{u}")
        lines.append(f"助手：{a[:150]}")
    return "\n".join(lines)

def build_search_query(question, history):
    """追问增强：当前问题 + 上一轮用户问题（解决"那毛利率呢"类追问）"""
    if history:
        return f"{question} {history[-1][0]}"
    return question

# ===== 统一入口 =====
def smart_answer(question: str) -> str:  
    """总调度：先路由，再分流（支持多轮对话 + 异常处理）"""  
    try:  
        # 追问增强：结合上一轮问题检索  
        search_q = build_search_query(question, history)  
        route_info = route_question(question, history)  
        route = route_info.get("route", "rag")  
        stock_code = route_info.get("stock_code")  
        metric = route_info.get("metric") or "营收"  
  
        print(f"[路由] 类型={route}, 股票={stock_code}, 指标={metric}")  
  
        # 分流（带异常兜底）  
        if route == "agent":  
            answer = ask_agent(question, stock_code)  
        elif route == "hybrid":  
            answer = ask_hybrid(search_q, stock_code, metric)  
        else:  
            answer = ask_rag(search_q)  
    except Exception as e:  
        answer = f"抱歉，处理您的问题时出错：{type(e).__name__}: {e}。请稍后重试或换个问法。"  
  
    # 记录历史（滑动窗口，最多 10 轮原始）  
    history.append((question, answer))  
    if len(history) > 10:  
        history.pop(0)  
    return answer

# ===== 主程序 =====
if __name__ == "__main__":
    print("FinRAG v0.4.1 协同系统（多轮对话版）已就绪！")
    print("输入 q 退出，输入 cls 清空历史\n")
    while True:
        q = input("你的问题: ").strip()
        if q.lower() == "q":
            break
        if q.lower() == "cls":
            history.clear()
            print("[已清空对话历史]\n")
            continue
        if not q:
            continue
        print("\n思考中...\n")
        ans = smart_answer(q)
        print(f"\n【回答】\n{ans}\n")

