# -*- coding: utf-8 -*-
"""数值评测：跑 10 题，输出答案供人工判定正确性"""
import json
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
    temperature=0.2,
)

# Few-Shot（与 ask.py 相同）
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

template = """你是一名资深金融研究助手，擅长从研报财务数据中提取和分析数值。
请先参考解题示例，再回答【问题】：
{few_shot_examples}

回答规则：
1. 只用【研报内容】回答，不要编造
2. 财务预测表数值按时间从左到右排列；A=实际值，E=预测值
3. 引用资料处标注编号 [n]
4. 需要计算的，先列算式再给结果
5. 数字保留原值并标注单位
6. 内容与问题无关时才回答"未找到相关信息"

【研报内容】
{context}

【问题】
{question}

【回答】"""

chain = PromptTemplate.from_template(template) | llm | StrOutputParser()

questions = json.loads(Path("data/eval/numerical_questions.json").read_text(encoding="utf-8"))

results = []
for item in questions:
    q = item["question"]
    q_emb = model.encode([q], normalize_embeddings=True).tolist()
    r = collection.query(query_embeddings=q_emb, n_results=10)
    parts = []
    for i, (doc, meta) in enumerate(zip(r["documents"][0], r["metadatas"][0]), start=1):
        parts.append(f"[{i}] 来源：{meta['source_file']}\n{doc}\n")
    context = "\n".join(parts)

    answer = chain.invoke({"few_shot_examples": few_shot_examples, "context": context, "question": q})
    results.append({"question": q, "answer": answer})
    print(f"\n==========\n问题: {q}\n预期: {item['expected_note']}\n回答: {answer[:200]}")

# 保存评测结果
Path("data/eval/numerical_results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n评测结果已保存: data/eval/numerical_results.json")
