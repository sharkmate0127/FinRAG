# -*- coding: utf-8 -*-
"""把 data/chunks/chunks.jsonl 的 1323 个块向量化，存入 ChromaDB"""
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

# 1. 读取分块结果
chunk_file = Path("data/chunks/chunks.jsonl")
if not chunk_file.exists():
    print("找不到 chunks.jsonl，请先运行 chunk_texts.py")
    exit()

chunks = [json.loads(line) for line in chunk_file.read_text(encoding="utf-8").splitlines() if line.strip()]
print(f"共读取 {len(chunks)} 个 chunk")

# 2. 加载 bge 中文 embedding 模型（首次自动下载，约 1.3GB）
print("加载 bge-large-zh-v1.5 模型（首次运行需下载，耐心等待）...")
model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
print("模型加载完成")

# 3. 批量向量化（1323 条，CPU 约 3-8 分钟）
texts = [c["text"] for c in chunks]
print("开始向量化，请耐心等待...")
embeddings = model.encode(
    texts,
    batch_size=16,
    show_progress_bar=True,
    normalize_embeddings=True,  # 归一化后可用余弦相似度，配合 ChromaDB cosine
)
print(f"向量化完成，向量维度: {embeddings.shape[1]}")

# 4. 存入 ChromaDB（持久化到本地目录）
client = chromadb.PersistentClient(path="data/vector_db")
collection = client.get_or_create_collection(
    name="finrag_reports",
    metadata={"hnsw:space": "cosine"},  # 用余弦相似度衡量语义距离
)

ids = [c["chunk_id"] for c in chunks]
documents = [c["text"] for c in chunks]
metadatas = [{
    "source_file": c["source_file"],
    "date": c["date"],
    "broker": c["broker"],
    "stock_code": c["stock_code"],
    "title": c["title"],
    "chunk_index": c["chunk_index"],
} for c in chunks]

collection.upsert(ids=ids, documents=documents, embeddings=embeddings.tolist(), metadatas=metadatas)
print(f"入库完成！向量库现有 {collection.count()} 条")
