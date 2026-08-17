# -*- coding: utf-8 -*-
"""检索对比实验：单一向量 vs 混合 vs 混合+重排（Hit Rate）"""
import jieba
import json
from pathlib import Path
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb

print("加载模型（reranker 首次运行需下载，耐心等待）...")
model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
reranker = CrossEncoder("BAAI/bge-reranker-large", max_length=512)
client = chromadb.PersistentClient(path="data/vector_db")
collection = client.get_collection("finrag_reports")

# 加载 chunks（BM25 用）
chunks = [json.loads(l) for l in Path("data/chunks/chunks.jsonl").read_text(encoding="utf-8").splitlines()]
texts = [c["text"] for c in chunks]
tokens = [list(jieba.cut(t)) for t in texts]
bm25 = BM25Okapi(tokens)
id2idx = {c["chunk_id"]: i for i, c in enumerate(chunks)}

# 测试集：问题 -> 期望股票代码（覆盖 10 家公司）
tests = [
    ("宁德时代的营收预测是多少", "300750"),
    ("比亚迪2026年净利润预测", "002594"),
    ("中科曙光的主营业务", "603019"),
    ("金山办公的WPS业务", "688111"),
    ("科大讯飞的产品体系", "002230"),
    ("阳光电源的储能业务", "300274"),
    ("浪潮信息AI服务器", "000977"),
    ("隆基绿能的BC电池", "601012"),
    ("工业富联的AI业务", "601138"),
    ("拓普集团的机器人业务", "601689"),
]

# ===== 三种检索 =====
def search_vec(query, n=20):
    q_emb = model.encode([query], normalize_embeddings=True).tolist()
    r = collection.query(query_embeddings=q_emb, n_results=n)
    return r["ids"][0]

def search_hybrid(query, n=20):
    vec_ids = set(search_vec(query, n))
    scores = bm25.get_scores(list(jieba.cut(query)))
    bm25_ids = {chunks[i]["chunk_id"] for i in
                sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]}
    return list(vec_ids | bm25_ids)

def rerank(query, ids, top=10):
    if not ids:
        return []
    docs = [chunks[id2idx[i]]["text"][:512] for i in ids]
    scores = reranker.predict([(query, d) for d in docs])
    ranked = [ids[i] for i in sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)]
    return ranked[:top]

def hit_rate(name, search_fn, do_rerank=False):
    hits = 0
    for q, code in tests:
        ids = search_fn(q, 20)
        if do_rerank:
            ids = rerank(q, ids, 10)
        top_codes = []
        for i in ids[:10]:
            idx = id2idx.get(i)
            if idx is not None:
                top_codes.append(chunks[idx]["stock_code"])
        if code in top_codes:
            hits += 1
    rate = hits / len(tests) * 100
    print(f"{name}: Hit Rate = {rate:.0f}% ({hits}/{len(tests)})")
    return rate

print("\n=== 检索对比实验开始 ===")
r1 = hit_rate("单一向量检索        ", search_vec)
r2 = hit_rate("混合检索(向量+BM25) ", search_hybrid)
r3 = hit_rate("混合+重排           ", search_hybrid, do_rerank=True)

best = max([("单一向量", r1), ("混合", r2), ("混合+重排", r3)], key=lambda x: x[1])
print(f"\n结论：最优方案 = {best[0]}（{best[1]:.0f}%）")
