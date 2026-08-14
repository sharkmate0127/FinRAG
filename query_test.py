# -*- coding: utf-8 -*-
"""测试向量检索：问几个问题，看 Top5 结果是否相关"""
from sentence_transformers import SentenceTransformer
import chromadb

model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
client = chromadb.PersistentClient(path="data/vector_db")
collection = client.get_collection("finrag_reports")

questions = ["宁德时代2022年营收情况", "比亚迪的净利润是多少"]

for q in questions:
    print(f"\n========== 查询：{q} ==========")
    emb = model.encode([q], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=emb, n_results=5)

    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    )):
        print(f"Top{i+1} 距离{dist:.4f} [{meta['stock_code']}] {meta['source_file']}")
        print("   ", doc[:80].replace("\n", " "))
