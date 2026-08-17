# -*- coding: utf-8 -*-
"""FinRAG v0.5：混合检索(向量+BM25) + Reranker精排 + Few-Shot数值推理 + 编号引用"""
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

# 加载 chunks（BM25 检索用）
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

# ===== Few-Shot 数值推理示例（Day 16-17）=====
few_shot_examples = """示例1：
问题：宁德时代2022年的营收是多少？
研报内容：2022A 2023A 2024E，营收（亿元）：3285.94 4009.17 4680.43
回答：宁德时代2022年营收为3285.94亿元[1]。（注：A代表实际值，E代表预测值）

示例2：
问题：比亚迪2025年净利润相比2024年预测增长了多少？
研报内容：归母净利润（亿元）：2024E 381，2025E 461，2026E 555
回答：比亚迪2025年预测净利润461亿元，2024年预测为381亿元。
增长率为 (461-381)/381 ≈ 21.0%[3]。

示例3：
问题：某公司2023年营收80亿，2024年营收100亿，2024年营收增长率是多少？
研报内容：营收（亿元）：2023A 80，2024A 100
回答：增长率为 (100-80)/80 = 25%[2]。
"""

# ===== Prompt 模板（P3 + 数值 + 编号引用）=====
template = """你是一名资深金融研究助手，擅长从研报财务数据中提取和分析数值。

请先参考以下解题示例，再回答用户的【问题】：

{few_shot_examples}

回答规则：
1. 只用【研报内容】回答，不要编造
2. 财务预测表中数值按时间从左到右排列；A=实际值，E=预测值
3. 引用研报信息时在句末标注编号，如"...营收3800亿[3]"
4. 涉及多家公司/年份时主动对比综合分析
5. 需要计算的，先列算式再给结果
6. 数字保留原值并标注单位（亿元/%）
7. 内容与问题完全无关时才回答"未找到相关信息"

【研报内容】
{context}

【问题】
{question}

【回答】"""

prompt = PromptTemplate.from_template(template)
chain = prompt | llm | StrOutputParser()

# ===== 混合检索 + 重排（Day 18 实验胜出方案）=====
def hybrid_retrieve(question: str, top: int = 10):
    # 1. 向量检索 Top20（语义）
    q_emb = model.encode([question], normalize_embeddings=True).tolist()
    vec_ids = collection.query(query_embeddings=q_emb, n_results=20)["ids"][0]

    # 2. BM25 检索 Top20（关键词）
    scores = bm25.get_scores(list(jieba.cut(question)))
    bm25_ids = {chunks[i]["chunk_id"] for i in
                sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:20]}

    # 3. 合并去重
    merged = [i for i in list(set(vec_ids) | bm25_ids) if i in id2idx]

    # 4. Reranker 精排取 Top10
    docs = [chunks[id2idx[i]]["text"][:512] for i in merged]
    scores_rerank = reranker.predict([(question, d) for d in docs])
    ranked = [merged[i] for i in
              sorted(range(len(scores_rerank)), key=lambda i: scores_rerank[i], reverse=True)][:top]
    return ranked

def ask(question: str):
    ranked = hybrid_retrieve(question, top=10)

    sources = []
    parts = []
    for i, cid in enumerate(ranked, start=1):
        chunk = chunks[id2idx[cid]]
        sources.append({"number": i, "source_file": chunk["source_file"],
                        "stock_code": chunk["stock_code"], "chunk_preview": chunk["text"][:60]})
        parts.append(f"[{i}] 来源：{chunk['source_file']}\n{chunk['text']}\n")
    context = "\n".join(parts)

    answer = chain.invoke({"few_shot_examples": few_shot_examples,
                           "context": context, "question": question})

    cited = sorted(set(int(n) for n in re.findall(r"$$(\d{1,2})$$", answer)))
    cited_sources = [s for s in sources if s["number"] in cited]
    return answer, cited_sources

if __name__ == "__main__":
    print("FinRAG v0.5 已就绪（混合检索+重排）！输入 q 退出\n")
    while True:
        q = input("你的问题: ").strip()
        if q.lower() == "q":
            break
        if not q:
            continue
        print("\n思考中...\n")
        answer, cited = ask(q)
        print(f"【回答】\n{answer}\n")
        print("【引用来源】")
        for c in cited:
            print(f"  [{c['number']}] {c['source_file']}")
            print(f"     原文: {c['chunk_preview']}...")
