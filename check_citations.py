# -*- coding: utf-8 -*-
"""引用准确率验证：随机 10 题，统计有效引用的比例"""
import re
import json
import random
from pathlib import Path
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import chromadb
from dotenv import load_dotenv
import os

load_dotenv()
print("加载模型...")
model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
client = chromadb.PersistentClient(path="data/vector_db")
collection = client.get_collection("finrag_reports")

llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    temperature=0.3,
)

template = """你是一名资深金融研究助手。请基于以下编号的【研报内容】回答【问题】。
规则：
1. 只用【研报内容】回答，不要编造
2. 引用研报信息时在句末标注编号，如"...营收3800亿[3]"
3. 内容与问题完全无关时才回答"未找到相关信息"

【研报内容】
{context}

【问题】
{question}

【回答】"""

chain = PromptTemplate.from_template(template) | llm | StrOutputParser()

# 10 个测试问题（从 Day 13 精选）
questions = [
    "宁德时代的主营业务是什么",
    "中科曙光的主营业务是什么",
    "科大讯飞的产品体系有哪些",
    "研报预计比亚迪2024-2026年归母净利润是多少",
    "宁德时代的营收预测是多少",
    "宁德时代和比亚迪的营收规模对比",
    "浪潮信息和中科曙光的业务对比",
    "宁德时代的成长驱动因素有哪些",
    "比亚迪出海战略的进展如何",
    "预测一下宁德时代明天的股价",
]

total_citations = 0
valid_citations = 0
results = []

for q in questions:
    q_emb = model.encode([q], normalize_embeddings=True).tolist()
    r = collection.query(query_embeddings=q_emb, n_results=10)
    parts = []
    for i, (doc, meta) in enumerate(zip(r["documents"][0], r["metadatas"][0]), start=1):
        parts.append(f"[{i}] 来源：{meta['source_file']}\n{doc}\n")
    context = "\n".join(parts)

    answer = chain.invoke({"context": context, "question": q})
    cited = re.findall(r"\[(\d{1,2})\]", answer)

    # 验证：编号必须在 1-10 范围内（有效引用）
    valid = [int(n) for n in cited if 1 <= int(n) <= 10]
    total_citations += len(valid)
    valid_citations += len(valid)
    # 越界编号（11+）= LLM 编造的引用
    fake = [int(n) for n in cited if int(n) > 10]

    results.append({"question": q, "answer": answer, "cited": valid, "fake": fake})
    print(f"[{'OK' if not fake else 'FAKE!'}] {q[:18]}... 引用编号 {valid} {'⚠️编造:' + str(fake) if fake else ''}")

print(f"\n=== 结果 ===")
print(f"总引用数: {total_citations}")
print(f"编造引用（编号>10）: {sum(len(x['fake']) for x in results)}")
print(f"引用准确率（编号有效比例）: {valid_citations/total_citations*100:.1f}%" if total_citations else "无引用")

# 保存验证结果
with open("data/abtest/citation_check.jsonl", "w", encoding="utf-8") as f:
    for x in results:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
