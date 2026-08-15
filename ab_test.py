# -*- coding: utf-8 -*-
"""A/B 测试：4 种 Prompt × 10 个测试问题，自动生成回答供人工评分"""
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import chromadb
from dotenv import load_dotenv
import os
import json

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

# ===== 4 种 Prompt 模板 =====
P0 = """回答问题：{question}
{context}"""

P1 = """你是一名金融研究助手。请基于以下【研报内容】回答用户的【问题】。
要求：只用【研报内容】回答，不要编造；如果研报内容不包含答案，回答"未找到相关信息"；回答末尾标注引用来源。

【研报内容】
{context}

【问题】
{question}

【回答】"""

P2 = """你是一名金融研究助手，擅长从金融研报中提取和分析数据。请基于【研报内容】回答【问题】。
要求：
1. 只用【研报内容】回答，不要编造
2. 涉及数字时保留研报原值并标注单位（如"亿元"、"%"）
3. 涉及表格数据时，说明是"XX年预测值"
4. 如果研报内容不包含答案，回答"未找到相关信息"
5. 回答末尾标注引用来源（来源：XX研报）

【研报内容】
{context}

【问题】
{question}

【回答】"""

P3 = """你是一名资深金融研究助手。请基于【研报内容】回答【问题】。
要求：
1. 只用【研报内容】回答，不要编造
2. 如果内容涉及多家公司/多个年份，主动做对比和综合分析
3. 涉及数字时保留原值并标注单位；涉及预测时说明"XX年预测值"
4. 推理类问题：从研报中提取"驱动因素、竞争优势、趋势"等信息组织回答
5. 只有当【研报内容】与问题完全无关时，才回答"未找到相关信息"
6. 回答末尾标注引用来源（来源：XX研报）

【研报内容】
{context}

【问题】
{question}

【回答】"""

templates = {"P0": P0, "P1": P1, "P2": P2, "P3": P3}

# ===== 10 个测试问题（覆盖四类）=====
test_questions = [
    # ===== 事实类（研报必有公司介绍章节）=====
    "宁德时代的主营业务是什么",
    "中科曙光的主营业务是什么",
    "科大讯飞的产品体系有哪些",

    # ===== 数值类（研报必有"盈利预测"表格）=====
    "研报预计比亚迪2024-2026年归母净利润是多少",
    "研报预计拓普集团2024-2026年的净利润是多少",
    "宁德时代的营收预测是多少",

    # ===== 对比类（同行业公司，检索易同时命中）=====
    "宁德时代和比亚迪的营收规模对比",
    "浪潮信息和中科曙光的业务对比",

    # ===== 推理类（研报必有"成长驱动/竞争优势"章节）=====
    "宁德时代的成长驱动因素有哪些",
    "比亚迪出海战略的进展如何",

    # ===== 越界类（应拒绝）=====
    "预测一下宁德时代明天的股价",
    "现在买入比亚迪股票能赚钱吗",
]

# ===== 检索函数（Top10，修复 Day 11-12 的问题）=====
def retrieve(question, n=10):
    emb = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=emb, n_results=n)
    parts = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        parts.append(f"[{meta['source_file']}]\n{doc}\n")
    return "\n".join(parts)

# ===== 跑 A/B 测试 =====
os.makedirs("data/abtest", exist_ok=True)
output = []

for pname, template in templates.items():
    chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
    for q in test_questions:
        context = retrieve(q)
        answer = chain.invoke({"context": context, "question": q})
        output.append({"prompt": pname, "question": q, "answer": answer})
        print(f"[{pname}] {q[:18]}... 完成")

with open("data/abtest/ab_results.jsonl", "w", encoding="utf-8") as f:
    for item in output:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
print(f"\n全部完成！共 {len(output)} 条回答，保存在 data/abtest/ab_results.jsonl")
