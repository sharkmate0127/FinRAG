# -*- coding: utf-8 -*-
"""验证 data/raw 里所有 PDF 能否被 PyMuPDF 打开并提取文本"""
import pymupdf as fitz
import os

pdf_dir = "data/raw"
os.makedirs(pdf_dir, exist_ok=True)  # 目录不存在会自动创建，不报错
ok_count = 0
total = 0

for fname in sorted(os.listdir(pdf_dir)):
    if not fname.endswith(".pdf"):
        continue
    total += 1
    path = os.path.join(pdf_dir, fname)
    try:
        doc = fitz.open(path)
        pages = len(doc)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        chars = len(text.strip())
        if chars > 500:
            ok_count += 1
            mark = "OK "
        else:
            mark = "WARN"
        print(f"{mark} {fname}: {pages}页, 提取{chars}字符")
    except Exception as e:
        print(f"FAIL {fname}: {e}")

print(f"\n结果: {ok_count}/{total} 份可正常提取文本")
