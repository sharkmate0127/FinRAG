# -*- coding: utf-8 -*-
"""app.py - Day 29：FastAPI 后端服务

接口：
- GET  /health       健康检查
- POST /query        研报问答（RAG 路线）
- POST /agent_query  Agent 工具调用（实时数据）
"""
import os
import json
import time
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ===== 日志 =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("finrag")

# ===== 导入核心系统（复用 ask.py 的 RAG 与 rag_agent.py 的协同）=====
print("加载模型（首次运行需下载，请等待）...")
from ask import ask, hybrid_retrieve  # noqa: E402

# 尝试导入协同系统；失败则降级只用 RAG
try:
    from rag_agent import smart_answer
    HAS_AGENT = True
except Exception as e:
    logger.warning(f"rag_agent 导入失败，仅提供 RAG 接口: {e}")
    HAS_AGENT = False

app = FastAPI(
    title="FinRAG 金融研报智能问答系统",
    description="RAG + Agent 双架构后端 API",
    version="0.5.0",
)

# ===== 请求/响应模型 =====
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list = []
    elapsed_ms: float = 0.0

class HealthResponse(BaseModel):
    status: str
    has_agent: bool
    chunk_count: int

# ===== 接口 1：健康检查 =====
@app.get("/health", response_model=HealthResponse)
def health():
    """检查服务是否正常"""
    try:
        chunk_count = len(Path("data/chunks/chunks.jsonl").read_text(encoding="utf-8").splitlines())
    except Exception:
        chunk_count = 0
    return HealthResponse(status="ok", has_agent=HAS_AGENT, chunk_count=chunk_count)

# ===== 接口 2：研报问答（RAG 路线）=====
@app.post("/query", response_model=QueryResponse)
def query_rag(req: QueryRequest):
    """研报内容问答（走 RAG：检索 + 生成 + 引用）"""
    start = time.time()
    try:
        answer, cited = ask(req.question)
        sources = [{"file": c["source_file"], "preview": c["chunk_preview"]} for c in cited]
        return QueryResponse(answer=answer, sources=sources, elapsed_ms=(time.time() - start) * 1000)
    except Exception as e:
        logger.error(f"/query 失败: {e}")
        raise HTTPException(status_code=500, detail=f"RAG 处理失败: {type(e).__name__}: {e}")

# ===== 接口 3：Agent 问答（实时数据路线）=====
@app.post("/agent_query", response_model=QueryResponse)
def query_agent(req: QueryRequest):
    """实时数据问答（Agent 工具调用）或 RAG+Agent 协同"""
    start = time.time()
    if not HAS_AGENT:
        raise HTTPException(status_code=503, detail="Agent 模块未加载")
    try:
        answer = smart_answer(req.question)
        return QueryResponse(answer=answer, sources=[], elapsed_ms=(time.time() - start) * 1000)
    except Exception as e:
        logger.error(f"/agent_query 失败: {e}")
        raise HTTPException(status_code=500, detail=f"Agent 处理失败: {type(e).__name__}: {e}")

# ===== 接口 4：请求日志中间件 =====
@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({time.time()-start:.2f}s)")
    return response
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
            
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
