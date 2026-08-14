# -*- coding: utf-8 -*-
"""FinRAG v0.1：完整 RAG 问答管线
流程：问题 → ChromaDB 检索 Top5 → 拼接上下文 → DeepSeek 生成 → 带引用回答
"""
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import chromadb
from dotenv import load_dotenv
import os

load_dotenv()  # 读取 .env 里的 DEEPSEEK_API_KEY

# ===== 1. 加载 embedding 模型（用于把问题变成向量）=====
print("加载模型...")
model = SentenceTransformer("BAAI/bge-large-zh-v1.5")

# ===== 2. 连接向量库 =====
client = chromadb.PersistentClient(path="data/vector_db")
collection = client.get_collection("finrag_reports")

# ===== 3. 配置 DeepSeek 大模型 =====
llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    temperature=0.3,
)

# ===== 4. Prompt 模板（RAG 的灵魂：约束模型只用研报内容回答）=====
template = """你是一名金融研究助手。请基于以下【研报内容】回答用户的【问题】。

要求：
1. 只用【研报内容】里的信息回答，不要编造任何数据
2. 如果多份研报涉及不同公司/不同年份，**主动做对比和综合**，不要说"未找到"
3. 即使研报没有直接给出结论，也可以从各家数据里提取关键数字/趋势
4. 数字保留研报原值，单位要标明
5. 如果【研报内容】真的与问题完全无关，才回答"未在研报中找到相关信息"
6. 回答末尾标注引用来源（格式：来源：XX研报）

【研报内容】
{context}

【问题】
{question}

【回答】"""

prompt = PromptTemplate.from_template(template)
chain = prompt | llm | StrOutputParser()  # LCEL 管道

# ===== 5. 核心问答函数 =====
def ask(question: str) -> str:
    # 5.1 把问题编码成向量
    q_emb = model.encode([question], normalize_embeddings=True).tolist()

    # 5.2 检索最相关的 5 个段落
    results = collection.query(query_embeddings=q_emb, n_results=10)

    # 5.3 拼上下文（每段标注来源，供 LLM 引用）
    parts = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        parts.append(f"[{meta['source_file']}]\n{doc}\n")
    context = "\n".join(parts)

    # 5.4 送 LLM 生成
    return chain.invoke({"context": context, "question": question})

# ===== 6. 主程序：交互式问答 =====
if __name__ == "__main__":
    print("FinRAG v0.1 已就绪！输入问题开始对话（输入 q 退出）\n")
    while True:
        q = input("你的问题: ").strip()
        if q.lower() == "q":
            break
        if not q:
            continue
        print("\n思考中，请稍等...\n")
        answer = ask(q)
        print(f"【回答】\n{answer}\n")
