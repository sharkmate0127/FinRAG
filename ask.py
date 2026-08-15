# -*- coding: utf-8 -*-
"""FinRAG v0.2：P3 最优 Prompt + Top10 检索"""
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

# P3 最优模板（A/B 测试胜出：2.6分）
template = """你是一名资深金融研究助手。请基于【研报内容】回答【问题】。
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

prompt = PromptTemplate.from_template(template)
chain = prompt | llm | StrOutputParser()

def ask(question: str) -> str:
    q_emb = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=q_emb, n_results=10)  # Top10
    parts = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        parts.append(f"[{meta['source_file']}]\n{doc}\n")
    context = "\n".join(parts)
    return chain.invoke({"context": context, "question": question})

if __name__ == "__main__":
    print("FinRAG v0.2 已就绪（P3 最优Prompt）！输入 q 退出\n")
    while True:
        q = input("你的问题: ").strip()
        if q.lower() == "q":
            break
        if not q:
            continue
        print("\n思考中...\n")
        print(f"【回答】\n{ask(q)}\n")
