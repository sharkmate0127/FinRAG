# P1-3 /upload_pdf 增量入库接口 —— 小白手把手步骤

> 适用：FinRAG v1.1.1（2026-09-05）
> 目标：让 FastAPI 多一个 `POST /upload_pdf`，上传研报 PDF → 自动分块 → 入库 → 立即可在 `/query` 问它。
> 全程**你亲手做**，下面每一段都是"贴到哪、贴什么、会看到什么"。

---

## 0. 为什么不能照旧指南做（先读懂这 3 个真相）

| # | 你原以为（旧指南） | 实际情况（AI 已勘察仓库） |
|---|---|---|
| 1 | `build_vector_db.py` 里有 `add_pdf_to_db` 函数 | ❌ **不存在**。它和 `chunk_texts.py` 一样是纯"顶层脚本"，**零函数**，没法 import |
| 2 | 往 ChromaDB 塞完向量，新 PDF 就能被问到 | ❌ **不行**。`ask.py` 的检索是混合检索：除了向量库，还有 **BM25** 和 **id2idx** 两个**内存对象**，启动时从 `data/chunks/chunks.jsonl` 一次性构建。只写向量库、不动这俩 → 新块在 BM25 那一路永远捞不到 |
| 3 | 要改 `chunk_texts.py` 加 `chunk_document` | ❌ 不必。**新建一个 `upload_pdf_tool.py`** 更干净，原文件一行不动 |

所以本手册的改动 = **3 个文件**：
1. `ask.py` —— 把内存索引构建包成 `_reload_index()` 函数（上传后可重载）
2. `upload_pdf_tool.py` —— **新建**，增量入库核心（解析→分块→追加 jsonl→向量化→upsert→重载）
3. `app.py` —— 末尾加 `/upload_pdf` 接口

---

## 1. 改 `ask.py`（约 5 分钟）

### 定位
VS Code 打开 `ask.py`，找到 **第 27-31 行**，现在长这样：

```python
chunks = [json.loads(l) for l in Path("data/chunks/chunks.jsonl").read_text(encoding="utf-8").splitlines()]
texts = [c["text"] for c in chunks]
tokens = [list(jieba.cut(t)) for t in texts]
bm25 = BM25Okapi(tokens)
id2idx = {c["chunk_id"]: i for i, c in enumerate(chunks)}
```

### 操作
**全选这 5 行删除**，粘贴下面的代码（一个函数 + 一次调用，效果和原来完全一样，只是以后能重复调用）：

```python
def _reload_index():
    """重载 chunks/bm25/id2idx 内存索引。
    顶层加载一次；/upload_pdf 增量入库后再次调用，
    让新 PDF 的 chunk 进入 BM25 与 id2idx（否则新块永远检索不到）。"""
    global chunks, tokens, bm25, id2idx
    chunks = [json.loads(l) for l in Path("data/chunks/chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    texts = [c["text"] for c in chunks]
    tokens = [list(jieba.cut(t)) for t in texts]
    bm25 = BM25Okapi(tokens)
    id2idx = {c["chunk_id"]: i for i, c in enumerate(chunks)}


_reload_index()
```

**Ctrl+S 保存。**

### 验证（确保没改坏）
小黑窗跑：
```powershell
python -c "import ask; print(len(ask.chunks), '个chunk, BM25就绪')"
```
预期：`1323 个chunk, BM25就绪`（数字可能是 1323 或你库里的总数，等于 `data\chunks\chunks.jsonl` 行数即可）。

---

## 2. 新建 `upload_pdf_tool.py`（约 10 分钟）

VS Code **右键左侧文件列表 → 新建文件** → 命名为 **`upload_pdf_tool.py`**（注意：在项目根目录 E:\finrag\FinRAG 下，不是别的文件夹）→ **全选粘贴下面全部内容** → Ctrl+S 保存：

```python
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
```

### 立刻自测（先不碰 FastAPI）
从 `data\raw\` 随便挑一份 PDF，命令行测试：
```powershell
python upload_pdf_tool.py "data\raw\20220617_开源证券_300750_宁德时代深度绑定核心客户.pdf"
```
预期结尾：
```
=== 入库成功 ===
  status: ok
  added_chunks: 30
  vector_total: 1353
  bm25_total: 1353
```
> `vector_total` 应比原来（1323）大，说明向量库和 BM25 都多了新块。
> 因为刚才重名自动加了时间戳后缀，所以不会覆盖原研报（再跑一次会再 +N 块，可反复测）。

---

## 3. 改 `app.py` 加 `/upload_pdf` 接口（约 10 分钟）

VS Code 打开 `app.py`，滚动到**文件最末尾**（约第 103 行 `uvicorn.run(...)` 上面），**把下面整块代码粘贴到 `if __name__ == "__main__":` 那一行的前面**：

```python
# ===== 接口 4（P1-3）：上传 PDF 增量入库，立即可问 =====
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from upload_pdf_tool import add_pdf_to_db


@app.post("/upload_pdf")
def upload_pdf(file: UploadFile = File(...)):
    """上传 PDF → 解析分块 → 增量入库 → 立即可在 /query 提问"""
    # 1. 校验文件类型
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse({"status": "error", "msg": "仅支持 .pdf 文件"}, status_code=400)

    # 2. 存临时文件（UploadFile 不能直接喂给 PDF 解析库）
    import tempfile
    import shutil
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # 3. 增量入库（核心逻辑在 upload_pdf_tool.py）
        result = add_pdf_to_db(tmp_path)
        return {
            "status": "ok",
            "filename": file.filename,
            "added_chunks": result["added_chunks"],
            "vector_total": result["vector_total"],
            "msg": f"已入库 {result['added_chunks']} 块（向量库共 {result['vector_total']} 块），立即可在 /query 提问",
        }
    except Exception as e:
        logger.error(f"/upload_pdf 失败: {e}")
        return JSONResponse({"status": "error", "msg": f"{type(e).__name__}: {e}"}, status_code=500)
    finally:
        if tmp_path and Path(tmp_path).exists():
            Path(tmp_path).unlink()  # 清理临时文件
```

> 注意：`app.py` 顶部第 13 行已 `from pathlib import Path`，所以 `Path(tmp_path)` 可用。
> 这段要在 `if __name__ == "__main__":` **之前**，别贴到最末尾的 main 块里面。

**Ctrl+S 保存。**

---

## 4. 端到端测试（约 10 分钟）

### 4.1 启动 FastAPI
新开 PowerShell 窗口：
```powershell
cd E:\finrag\FinRAG
.venv\Scripts\activate
$env:HF_ENDPOINT = "https://hf-mirror.com"
python -m uvicorn app:app --port 8000
```
预期：`Uvicorn running on http://127.0.0.1:8000`（首次加载模型要等几十秒，别 Ctrl+C）。

### 4.2 Swagger 上传测试
浏览器打开 `http://127.0.0.1:8000/docs` → 应该能看到 **4 个接口**（GET /health、POST /query、POST /agent_query、**POST /upload_pdf**）。

点开 **POST /upload_pdf** → **Try it out** → **Choose File** 选一份 `data\raw\` 下的 PDF → **Execute**。

**成功响应**：
```json
{
  "status": "ok",
  "filename": "20230411_信达证券_688111_金山办公CB.pdf",
  "added_chunks": 47,
  "vector_total": 1447,
  "msg": "已入库 47 块（向量库共 1447 块），立即可在 /query 提问"
}
```

### 4.3 验证闭环：问刚上传的 PDF
回到 Swagger **POST /query**，Body 填：
```json
{ "question": "金山办公这份CB研报的核心观点是什么" }
```
**预期**：返回 `sources` 里能看到 `20230411_信达证券_688111_金山办公CB.txt` 或带时间戳后缀的新 source_file —— 证明新 PDF 已被检索到。

---

## 5. 排错对照

| 现象 | 原因 | 修复 |
|---|---|---|
| `ModuleNotFoundError: No module named 'upload_pdf_tool'` | 文件没建在项目根目录 | 确认 `E:\finrag\FinRAG\upload_pdf_tool.py` 存在（跟 app.py 同级） |
| `ImportError: cannot import name '_reload_index'` | ask.py 没保存 | 回到第 1 步，确认保存后重开 uvicorn |
| 上传返回 `400 仅支持 .pdf` | 选的不是 PDF | 换 data\raw 里的 .pdf |
| `vector_total` 不变（还是 1323） | uvicorn 进程还是旧代码 | Ctrl+C 停掉，重跑第 4.1 步 |
| /query 问不到新 PDF | ask.py 没重载或 4.3 用词太偏 | 用文件标题里的词问；确认输出里有 `ask.py 内存索引已重载` |
| 报 `fitz` 相关错误 | 环境缺 PyMuPDF | 在激活的 .venv 下 `pip install pymupdf` |
| 上传 pdf 是扫描图片版 → 空内容 | 无文本层 | 论文里如实写"暂不支持 OCR 扫描件"当已知局限 |

---

## 6. 完成标志

- [ ] `python -c "import ask; print(len(ask.chunks))"` 输出正常
- [ ] CLI 自测（第 2 步）`=== 入库成功 ===` 且 `vector_total` > 原总数
- [ ] Swagger `/docs` 显示 4 个接口
- [ ] Swagger 上传 PDF 返回 `"status": "ok"`、`added_chunks > 0`
- [ ] `/query` 能问出含新 PDF source_file 引用的答案

## 7. 收尾 commit（你自己桌面终端跑）

```powershell
git add ask.py upload_pdf_tool.py app.py
git commit -m "P1-3: 新增/upload_pdf增量入库接口(解析-分块-入库-重载内存索引)"
git push origin main
```

> 提示：测试时多跑几次 CLI 会在 chunks.jsonl 和向量库留下重复块（不影响正确性）。想清干净重来：`git checkout -- ask.py app.py` + 删 `upload_pdf_tool.py`，再重新跑 `build_vector_db.py` 重建 1323 块向量库即可。
