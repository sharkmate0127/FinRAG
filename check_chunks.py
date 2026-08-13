# -*- coding: utf-8 -*-
"""抽查 chunks.jsonl 质量：字符分布 + 前2块预览 + 财务数据块"""
import json
from pathlib import Path

path = Path("data/chunks/chunks.jsonl")
if not path.exists():
    print("文件不存在！请先运行: python chunk_texts.py")
    exit()

records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(f"总块数: {len(records)}")

# 1. 字符数分布检查
chars = [r["char_count"] for r in records]
under = sum(1 for c in chars if c < 500)
ok = sum(1 for c in chars if 500 <= c <= 1000)
over = sum(1 for c in chars if c > 1000)
print(f"字符分布: <500: {under} | 500-1000: {ok} | >1000: {over}")

# 2. 前 2 块预览
print("\n=== 前 2 个块预览 ===")
for r in records[:2]:
    print(f"[{r['chunk_id']}] 来源={r['source_file']} 股票={r['stock_code']} 字符={r['char_count']}")
    print("文本前80字:", r["text"][:80].replace("\n", " "))
    print()

# 3. 找含财务数据的块（供 Day 12-13 数值推理用）
print("=== 含财务数据的块（营收/净利润/毛利率/%） ===")
found = 0
for r in records:
    if any(k in r["text"] for k in ["营收", "净利润", "毛利率", "同比增长", "%"]):
        print(f"[{r['chunk_id']}] 来源={r['source_file']} 字符={r['char_count']}")
        print("文本前100字:", r["text"][:100].replace("\n", " "))
        print()
        found += 1
        if found >= 2:
            break
