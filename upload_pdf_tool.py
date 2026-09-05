# -*- coding: utf-8 -*-
"""upload_pdf_tool.py - P1-3：单份 PDF 增量入库工具

把一份新研报 PDF：解析 → 分块 → 追加 chunks.jsonl → 向量化 →
upsert ChromaDB → 重载 ask.py 内存索引，使新内容立即可被检索问答。

用法（命令行自测）：
    python upload_pdf_tool.py <pdf路径>
被 app.py 的 /upload_pdf 调用：add_pdf_to_db(pdf_path)
"""
import json
import time
from pathlib import Path

# 兼容新旧版 langchain（与 chunk_texts.py 同款写法）
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

ROOT = Path(__file__).resolve().parent
CHUNK_FILE = ROOT / "data" / "chunks" / "chunks.jsonl"

# 分块参数必须与 chunk_texts.py 完全一致（800/100，同一分隔符集）
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", "。", "；", " ", ""],
    length_function=len,
)


def _extract_pdf_text(pdf_path):
    """用 PyMuPDF 抽全文（与 parse_pdfs.py 同款）"""
    import fitz
    doc = fitz.open(str(pdf_path))
    try:
        text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
    if not text or not text.strip():
        raise ValueError(f"PDF 解析结果为空（可能是扫描件/无文本层）：{Path(pdf_path).name}")
    return text


def _parse_meta_from_name(fname):
    """按命名规则解析元数据：YYYYMMDD_券商_代码_标题（与 chunk_texts.py 一致）"""
    base = fname
    parts = base.split("_", 3)
    if len(parts) >= 4:
        date, broker, stock_code, title = parts
    else:
        date = broker = stock_code = "未知"
        title = base
    return base, date, broker, stock_code, title


def add_pdf_to_db(pdf_path):
    """核心：单份 PDF 增量入库。返回统计 dict。
    流程：解析 → 分块 → 追加 chunks.jsonl → 向量化新增块 →
    upsert ChromaDB → 重载 ask.py 内存索引。
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"找不到 PDF 文件: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"仅支持 .pdf 文件: {pdf_path.name}")

    # 1. 解析全文
    text = _extract_pdf_text(pdf_path)
    print(f"[1/5] 解析完成: {pdf_path.name} ({len(text)} 字符)")

    # 2. 命名空间：防止与已有研报重名导致 chunk_id 冲突
    base, date, broker, stock_code, title = _parse_meta_from_name(pdf_path.stem)
    if _source_file_exists(base + ".txt"):
        base = f"{base}_{int(time.time())}"   # 重名则加时间戳后缀
        print(f"[warn] 源名已在库，自动改用 {base} 避免 chunk_id 冲突")
    source_file = base + ".txt"

    # 3. 分块
    chunks = splitter.split_text(text)
    print(f"[2/5] 分块完成: {len(chunks)} 块")

    records = []
    for i, chunk in enumerate(chunks):
        records.append({
            "chunk_id": f"{base}#{i:03d}",
            "source_file": source_file,
            "date": date,
            "broker": broker,
            "stock_code": stock_code,
            "title": title,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "char_count": len(chunk),
            "text": chunk,
        })

    # 4. 追加到 chunks.jsonl（原有的 1323 块一行不动，只在末尾追加）
    with CHUNK_FILE.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[3/5] 已追加 {len(records)} 块到 chunks.jsonl")

    # 5. 向量化新增块 + upsert ChromaDB + 重载 ask 内存索引
    import ask  # 复用 ask.py 已加载的 model/collection，不重复加载大模型
    model = ask.model
    collection = ask.collection

    new_texts = [r["text"] for r in records]
    print("[4/5] 向量化新增块（复用 bge 模型）...")
    embs = model.encode(new_texts, batch_size=16, normalize_embeddings=True).tolist()

    collection.upsert(
        ids=[r["chunk_id"] for r in records],
        documents=new_texts,
        embeddings=embs,
        metadatas=[{
            "source_file": r["source_file"],
            "date": r["date"],
            "broker": r["broker"],
            "stock_code": r["stock_code"],
            "title": r["title"],
            "chunk_index": r["chunk_index"],
        } for r in records],
    )
    print(f"[5/5] ChromaDB upsert 完成，库内总数: {collection.count()}")

    # 关键：重载 ask.py 内存索引，否则 BM25 捞不到新块
    ask._reload_index()
    print(f"      ask.py 内存索引已重载（BM25 语料 {len(ask.chunks)} 块）")

    return {
        "status": "ok",
        "source_file": source_file,
        "added_chunks": len(records),
        "vector_total": collection.count(),
        "bm25_total": len(ask.chunks),
    }


def _source_file_exists(source_file):
    """检查该 source_file 是否已在 chunks.jsonl"""
    if not CHUNK_FILE.exists():
        return False
    for line in CHUNK_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                if json.loads(line).get("source_file") == source_file:
                    return True
            except json.JSONDecodeError:
                continue
    return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python upload_pdf_tool.py <pdf路径>")
        sys.exit(1)
    try:
        result = add_pdf_to_db(sys.argv[1])
        print("\n=== 入库成功 ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"\n[入库失败] {type(e).__name__}: {e}")
        sys.exit(2)