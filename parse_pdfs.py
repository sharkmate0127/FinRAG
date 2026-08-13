# -*- coding: utf-8 -*-
"""把 data/raw 里所有 PDF 解析为文本，存到 data/parsed"""
import fitz
import os

raw_dir = "data/raw"
parsed_dir = "data/parsed"
os.makedirs(parsed_dir, exist_ok=True)

for fname in sorted(os.listdir(raw_dir)):
    if not fname.endswith(".pdf"):
        continue
    src = os.path.join(raw_dir, fname)
    doc = fitz.open(src)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    out_name = fname.replace(".pdf", ".txt")
    dst = os.path.join(parsed_dir, out_name)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"已解析: {fname} -> {out_name} ({len(text)}字符)")

print("\n全部解析完成！")
