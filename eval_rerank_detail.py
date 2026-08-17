# -*- coding: utf-8 -*-
"""精排质量对比：Top1/Top3 命中率 + MRR（反映排序质量）"""
import jieba
import json
from pathlib import Path
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb

print("加载模型...")
model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
reranker = CrossEncoder("BAAI/bge-reranker-large", max_length=512)
client = chromadb.PersistentClient(path="data/vector_db")
collection = client.get_collection("finrag_reports")

chunks = [json.loads(l) for l in Path("data/chunks/chunks.jsonl").read_text(encoding="utf-8").splitlines()]
texts = [c["text"] for c in chunks]
tokens = [list(jieba.cut(t)) for t in texts]
bm25 = BM25Okapi(tokens)
id2idx = {c["chunk_id"]: i for i, c in enumerate(chunks)}

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

def search_vec(query, n=20):
    q_emb = model.encode([query], normalize_embeddings=True).tolist()
    return collection.query(query_embeddings=q_emb, n_results=n)["ids"][0]

def search_hybrid(query, n=20):
    vec_ids = set(search_vec(query, n))
    scores = bm25.get_scores(list(jieba.cut(query)))
    bm25_ids = {chunks[i]["chunk_id"] for i in
                sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]}
    return list(vec_ids | bm25_ids)

def rerank(query, ids, top=10):
    if not ids:
        return []
    docs = [chunks[id2idx[i]]["text"][:512] for i in ids if i in id2idx]
    ids = [i for i in ids if i in id2idx]
    scores = reranker.predict([(query, d) for d in docs])
    ranked = [ids[i] for i in sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)]
    return ranked[:top]

def topk_stats(name, search_fn, do_rerank=False):
    top1 = top3 = mrr_sum = 0
    for q, code in tests:
        ids = search_fn(q, 20)
        if do_rerank:
            ids = rerank(q, ids, 10)
        else:
            ids = ids[:10]
        codes = [chunks[id2idx[i]]["stock_code"] for i in ids if i in id2idx]
        if codes and codes[0] == code:
            top1 += 1
        if code in codes[:3]:
            top3 += 1
        for rank, c in enumerate(codes, start=1):
            if c == code:
                mrr_sum += 1 / rank
                break
    n = len(tests)
    print(f"{name}: Top1={top1}/{n}  Top3={top3}/{n}  MRR={mrr_sum/n:.3f}")

print("\n=== 精排质量对比 ===\n")
topk_stats("单一向量检索         ", search_vec)
topk_stats("混合检索(向量+BM25)  ", search_hybrid)
topk_stats("混合+重排            ", search_hybrid, do_rerank=True)
