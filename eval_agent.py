# -*- coding: utf-8 -*-
"""eval_agent.py - Day 25：协同版检索验证 + 路由准确率测试

测试内容：
1. Hit Rate：协同版 hybrid_retrieve 在混合/普通问题上检索命中率
2. 路由准确率：route_question 判断 rag/agent/hybrid 是否正确
"""
import json
from pathlib import Path
import jieba
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb

print("加载模型（耐心等待）...")
model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
reranker = CrossEncoder("BAAI/bge-reranker-large", max_length=512)
client = chromadb.PersistentClient(path="data/vector_db")
collection = client.get_collection("finrag_reports")

chunks = [json.loads(l) for l in Path("data/chunks/chunks.jsonl").read_text(encoding="utf-8").splitlines()]
texts = [c["text"] for c in chunks]
tokens = [list(jieba.cut(t)) for t in texts]
bm25 = BM25Okapi(tokens)
id2idx = {c["chunk_id"]: i for i, c in enumerate(chunks)}

# ===== 协同版混合检索（与 rag_agent.py 保持一致）=====
def hybrid_retrieve(question: str, top: int = 10):
    q_emb = model.encode([question], normalize_embeddings=True).tolist()
    vec_ids = collection.query(query_embeddings=q_emb, n_results=20)["ids"][0]
    scores = bm25.get_scores(list(jieba.cut(question)))
    bm25_ids = {chunks[i]["chunk_id"] for i in
                sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:20]}
    merged = [i for i in list(set(vec_ids) | bm25_ids) if i in id2idx]
    docs = [chunks[id2idx[i]]["text"][:512] for i in merged]
    scores_rerank = reranker.predict([(question, d) for d in docs])
    ranked = [merged[i] for i in
              sorted(range(len(scores_rerank)), key=lambda i: scores_rerank[i], reverse=True)][:top]
    return ranked

# ===== 测试集 1：检索 Hit Rate（覆盖 10 家公司 + 混合类问题）=====
tests = [
    ("宁德时代的营收预测是多少", "300750"),
    ("比亚迪2026年净利润预测", "002594"),
    ("中科曙光的主营业务", "603019"),
    ("金山办公的WPS业务", "688111"),
    ("科大讯飞的产品体系", "002230"),
    ("阳光电源的储能业务", "300274"),
    ("浪潮信息AI服务器", "000977"),
    ("隆基绿能的BC电池", "601012"),
    ("研报说宁德时代营收增长20%，实际财报是多少", "300750"),
    ("比亚迪预测增速和实际增速对比", "002594"),
]

def hit_rate():
    hits = 0
    for q, code in tests:
        ranked = hybrid_retrieve(q, top=10)
        codes = [chunks[id2idx[cid]]["stock_code"] for cid in ranked if cid in id2idx]
        if code in codes:
            hits += 1
        else:
            print(f"  未命中: {q}")
    rate = hits / len(tests) * 100
    print(f"协同版检索 Hit Rate = {rate:.0f}% ({hits}/{len(tests)})")
    return rate

# ===== 测试集 2：路由准确率（期望路由标注）=====
route_tests = [
    ("宁德时代主营业务是什么", "rag"),
    ("宁德时代今天股价多少", "agent"),
    ("宁德时代最新行情", "agent"),
    ("研报说营收增长20%，实际是多少", "hybrid"),
    ("比亚迪预测和实际增速对比", "hybrid"),
    ("中科曙光2026年营收预测", "rag"),
    ("金山办公今天股价", "agent"),
    ("隆基绿能研报里的成本优势分析", "rag"),
    ("研报预测的宁德营收 vs 实际营收差距", "hybrid"),
    ("浪潮信息AI服务器市场份额", "rag"),
]

def route_accuracy():
    """路由验证：直接调用 rag_agent 的路由函数"""
    from rag_agent import route_question
    correct = 0
    for q, expect in route_tests:
        try:
            info = route_question(q)
            got = info.get("route", "rag")
            ok = "✅" if got == expect else f"❌(期望{expect})"
            print(f"  {ok} [{got:6s}] {q[:25]}")
            if got == expect:
                correct += 1
        except Exception as e:
            print(f"  ❌(异常) {q[:25]}: {e}")
    rate = correct / len(route_tests) * 100
    print(f"路由准确率 = {rate:.0f}% ({correct}/{len(route_tests)})")
    return rate

if __name__ == "__main__":
    print("\n=== 1. 协同版检索 Hit Rate ===")
    hit_rate()
    print("\n=== 2. 路由准确率 ===")
    route_accuracy()
    print("\n完成！")
