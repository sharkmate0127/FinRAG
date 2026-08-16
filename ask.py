# -*- coding: utf-8 -*-
"""FinRAG v0.4：数值推理增强版（Few-Shot + 表格引导）"""
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
    temperature=0.2,  # 数值题降低温度，回答更稳定
)

# ===== Few-Shot 示例（教模型读懂表格 + 算数）=====
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

template = """你是一名资深金融研究助手，擅长从研报财务数据中提取和分析数值。

请先参考以下解题示例，再回答用户的【问题】：

{few_shot_examples}

回答规则：
1. 只用【研报内容】回答，不要编造
2. 财务预测表中数值按时间从左到右排列；A=实际值，E=预测值
3. 回答中引用资料处标注编号 [n]
4. 需要计算的，先列算式再给结果（如"(461-381)/381≈21.0%"）
5. 数字保留原值并标注单位（亿元/%）
6. 内容与问题无关时才回答"未找到相关信息"

【研报内容】
{context}

【问题】
{question}

【回答】"""

prompt = PromptTemplate.from_template(template)
chain = prompt | llm | StrOutputParser()

def ask(question: str):
    q_emb = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=q_emb, n_results=10)

    sources = []
    parts = []
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), start=1):
        sources.append({"number": i, "source_file": meta["source_file"],
                        "stock_code": meta["stock_code"], "chunk_preview": doc[:60]})
        parts.append(f"[{i}] 来源：{meta['source_file']}\n{doc}\n")
    context = "\n".join(parts)

    answer = chain.invoke({
        "few_shot_examples": few_shot_examples,
        "context": context,
        "question": question,
    })

    cited = sorted(set(int(n) for n in re.findall(r"\[(\d{1,2})\]", answer)))
    cited_sources = [s for s in sources if s["number"] in cited]
    return answer, cited_sources

if __name__ == "__main__":
    print("FinRAG v0.4 已就绪（数值推理版）！输入 q 退出\n")
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

