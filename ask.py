# -*- coding: utf-8 -*-
"""FinRAG v0.3：编号引用溯源版
回答中用 [1][2] 标注引用编号，程序负责把编号映射回研报来源"""
import re
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

# 引用版 Prompt：要求回答中用 [n] 标注引用
template = """你是一名资深金融研究助手。请基于以下编号的【研报内容】回答【问题】。

规则：
1. 只用【研报内容】回答，不要编造
2. 引用研报中的信息时，在句末标注对应编号，格式如"宁德时代2024年营收预测为3800亿元[3]"
3. 涉及多家公司/年份时主动对比综合分析
4. 数字保留原值并标注单位；预测值说明"XX年预测值"
5. 内容与问题完全无关时才回答"未找到相关信息"

【研报内容】
{context}

【问题】
{question}

【回答】"""

prompt = PromptTemplate.from_template(template)
chain = prompt | llm | StrOutputParser()

def ask(question: str):
    # 1. 检索 Top10
    q_emb = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=q_emb, n_results=10)

    # 2. 带编号拼上下文（编号从 1 开始）
    sources = []  # 记录每个编号对应的来源
    parts = []
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), start=1):
        sources.append({
            "number": i,
            "source_file": meta["source_file"],
            "stock_code": meta["stock_code"],
            "title": meta["title"],
            "chunk_preview": doc[:60],  # 原文开头，用于展示
        })
        parts.append(f"[{i}] 来源：{meta['source_file']}\n{doc}\n")
    context = "\n".join(parts)

    # 3. 生成回答
    answer = chain.invoke({"context": context, "question": question})

    # 4. 解析回答中的 [n]，整理引用列表
    cited_numbers = sorted(set(int(n) for n in re.findall(r"\[(\d{1,2})\]", answer)))
    cited = [s for s in sources if s["number"] in cited_numbers]

    return answer, cited

if __name__ == "__main__":
    print("FinRAG v0.3 已就绪（编号引用版）！输入 q 退出\n")
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
        if cited:
            for c in cited:
                print(f"  [{c['number']}] {c['source_file']}")
                print(f"     原文章节预览: {c['chunk_preview']}...")
        else:
            print("  （回答未引用任何研报内容）")
