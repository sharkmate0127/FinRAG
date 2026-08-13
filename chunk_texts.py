# -*- coding: utf-8 -*-
"""把 data/parsed 里的 20 份研报切成 500-1000 字符的知识块
每个 chunk 带元数据：来源 PDF、日期、券商、股票代码、标题
输出：data/chunks/chunks.jsonl（每行一个 chunk，方便后续向量化）"""
import json
import os
from pathlib import Path

# 兼容新旧版 langchain
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

input_dir = Path("data/parsed")
output_dir = Path("data/chunks")
output_dir.mkdir(parents=True, exist_ok=True)

# 切分器：800 字符一块，重叠 100 字符
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", "。", "；", " ", ""],
    length_function=len,
)

all_chunks = []

for src_path in sorted(input_dir.glob("*.txt")):
    fname = src_path.name
    # 解析文件名：YYYYMMDD_券商_代码_标题.txt
    base = fname.replace(".txt", "")
    parts = base.split("_", 3)  # 最多分4段，避免标题里的下划线被拆
    if len(parts) >= 4:
        date, broker, stock_code, title = parts
    else:
        date = broker = stock_code = "未知"
        title = base

    text = src_path.read_text(encoding="utf-8")
    chunks = splitter.split_text(text)

    for i, chunk in enumerate(chunks):
        record = {
            "chunk_id": f"{base}#{i:03d}",
            "source_file": fname,
            "date": date,
            "broker": broker,
            "stock_code": stock_code,
            "title": title,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "char_count": len(chunk),
            "text": chunk,
        }
        all_chunks.append(record)

    print(f"已切分 {fname}: {len(chunks)} 块")

# 写出 jsonl（每行一个 JSON 对象）
out_file = output_dir / "chunks.jsonl"
with out_file.open("w", encoding="utf-8") as f:
    for r in all_chunks:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# 统计 + 检查
print(f"\n=== 分块完成 ===")
print(f"总块数: {len(all_chunks)}")
if all_chunks:
    chars = [r["char_count"] for r in all_chunks]
    avg = sum(chars) // len(chars)
    print(f"字符数: 平均 {avg}, 最小 {min(chars)}, 最大 {max(chars)}")
    over = sum(1 for c in chars if c > 1000)
    under = sum(1 for c in chars if c < 500)
    print(f"> 1000 字符: {over} 个（应 <5%）")
    print(f"< 500 字符: {under} 个（应 <10%）")
print(f"\n输出: {out_file}")
