# -*- coding: utf-8 -*-
"""FinRAG v0.6：多轮对话版（滑动窗口历史 + 追问检索增强）"""
import re
import json
from pathlib import Path
import jieba
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import chromadb
from dotenv import load_dotenv
import os

load_dotenv()

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

# Few-Shot 数值推理示例（Day 16-17）
few_shot_examples = """示例1：
问题：宁德时代2022年的营收是多少？
研报内容：2022A 2023A 2024E，营收（亿元）：3285.94 4009.17 4680.43
回答：宁德时代2022年营收为3285.94亿元[1]。（A=实际，E=预测）

示例2：
问题：比亚迪2025年净利润相比2024年预测增长了多少？
研报内容：归母净利润（亿元）：2024E 381，2025E 461，2026E 555
回答：增长率为 (461-381)/381 ≈ 21.0%[3]。

示例3：
问题：某公司2023年营收80亿，2024年营收100亿，2024年营收增长率是多少？
研报内容：营收（亿元）：2023A 80，2024A 100
回答：增长率为 (100-80)/80 = 25%[2]。
"""

# ===== 多轮对话模板：加入【对话历史】段 =====
template = """你是一名资深金融研究助手，擅长从研报财务数据中提取和分析数值。

请先参考以下解题示例：

{few_shot_examples}

回答规则：
1. 只用【研报内容】回答，不要编造
2. 财务预测表中数值按时间从左到右排列；A=实际值，E=预测值
3. 引用研报信息时在句末标注编号，如"...营收3800亿[3]"
4. 涉及多家公司/年份时主动对比综合分析
5. 需要计算的，先列算式再给结果
6. 数字保留原值并标注单位
7. **结合【对话历史】理解用户【问题】**，若问题是追问（如"那毛利率呢"），答案应延续上一轮讨论的公司
8. 内容与问题完全无关时才回答"未找到相关信息"

【对话历史】
{history}

【研报内容】
{context}

【问题】
{question}

【回答】"""

prompt = PromptTemplate.from_template(template)
chain = prompt | llm | StrOutputParser()

# ===== 混合检索 + 重排（Day 18 胜出方案）=====
def hybrid_retrieve(question: str, top: int = 10):
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

# ===== 对话历史管理（滑动窗口：最多保留 5 轮）=====
history = []  # [(user, assistant), ...]

def format_history(history):
    if not history:
        return "（无历史对话）"
    lines = []
    for u, a in history[-5:]:  # 滑动窗口
        lines.append(f"用户：{u}")
        lines.append(f"助手：{a[:200]}")  # 回答截断，控制 token
    return "\n".join(lines)

def build_search_query(question, history):
    """追问增强：当前问题 + 上一轮用户问题"""
    if history:
        return f"{question} {history[-1][0]}"
    return question

def ask(question: str):
    # 检索（结合上一轮问题，支持追问）
    search_q = build_search_query(question, history)
    ranked = hybrid_retrieve(search_q, top=10)

    sources = []
    parts = []
    for i, cid in enumerate(ranked, start=1):
        chunk = chunks[id2idx[cid]]
        sources.append({"number": i, "source_file": chunk["source_file"],
                        "stock_code": chunk["stock_code"], "chunk_preview": chunk["text"][:60]})
        parts.append(f"[{i}] 来源：{chunk['source_file']}\n{chunk['text']}\n")
    context = "\n".join(parts)

    answer = chain.invoke({
        "few_shot_examples": few_shot_examples,
        "history": format_history(history),
        "context": context,
        "question": question,
    })

    cited = sorted(set(int(n) for n in re.findall(r"\[(\d{1,2})\]", answer)))
    cited_sources = [s for s in sources if s["number"] in cited]
    return answer, cited_sources

#if __name__ == "__main__":
    print("FinRAG v0.6 已就绪（多轮对话版）！输入 q 退出，输入 cls 清空历史\n")
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
        answer, cited = ask(q)
        # 记录到历史（最多保留 10 轮原始，格式化时取 5 轮）
        history.append((q, answer))
        if len(history) > 10:
            history.pop(0)

        print(f"【回答】\n{answer}\n")
        print("【引用来源】")
        for c in cited:
            print(f"  [{c['number']}] {c['source_file']}")
            print(f"     原文: {c['chunk_preview']}...")
