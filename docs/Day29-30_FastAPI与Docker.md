# Day 29-30 小白操作指南：FastAPI 后端 + Docker 化部署

> 日期：2026-08-28 ｜ 项目：FinRAG v3.0 ｜ 导师方案：Day 31-32（第 5 周）  
> 你的 API 已切换 **DeepSeek**，代码沿用已验证配置。

---

## 一、先看导师要求（PDF 原文摘录）

### Day 31：FastAPI 后端

- 将 RAG+Agent 系统封装为 FastAPI 服务
- 定义 API 接口：`/query`、`/upload_pdf`、`/agent_query`、`/health`
- 异步支持 + 请求日志
- 检查点：**Swagger 文档可访问**（FastAPI 自带 `/docs` 页面）

### Day 32：Docker 化

- 写 Dockerfile（后端 + ChromaDB + Ollama）
- docker-compose.yml（一键启动全部服务）
- 测试容器化部署
- 检查点：docker-compose up 启动后服务正常

### 你的环境现状（我查过了）

| 项目                | 状态                         | 安排                  |
| ----------------- | -------------------------- | ------------------- |
| FastAPI + uvicorn | ✅ 已装（0.141.1 / 0.52.1）     | Day 29 直接做          |
| Docker            | ❌ 未装（需下载几百 MB + WSL2 + 重启） | Day 30 先写文件，部署可选    |
| Ollama 本地模型       | ❌ 未装（4GB+ 下载受限）            | Docker Compose 里先占位 |

---

## 二、核心概念解释（零基础版）

### 1. FastAPI 是什么？

大白话：把"你的 RAG+Agent 系统"变成一个**可以被任何程序调用的服务**。  
类比：以前你只能在终端里输入问题（像去柜台办事），FastAPI 让系统变成**自助取号机**——别人（网页、手机 App、其他程序）通过网址就能问它问题。

### 2. API 接口（Endpoint）是什么？

大白话：系统的"窗口"。

| 接口             | 作用              | 类比     |
| -------------- | --------------- | ------ |
| `/query`       | 问研报问题（RAG 路线）   | 问询窗口   |
| `/agent_query` | 问实时数据（Agent 路线） | 数据查询窗口 |
| `/upload_pdf`  | 上传新研报           | 收件窗口   |
| `/health`      | 检查系统活着没         | 体检窗口   |

### 3. Swagger 文档是什么？

FastAPI **自动生成**的 API 使用说明书页面。打开 `http://127.0.0.1:8000/docs` 就能看到所有接口，还能直接点击"试一试"——这是 FastAPI 最受欢迎的原因之一。

### 4. Docker 是什么？

大白话：**把整个系统装进一个标准箱子**（容器），在任何电脑上都能一键打开。  
类比：你写的 Python 程序在自己电脑能跑，但换台电脑就要重新配环境。Docker = **把"电脑环境+程序"一起打包**，别人拿到箱子直接跑。

### 5. Dockerfile vs docker-compose

- **Dockerfile**：一张"怎么造箱子"的图纸（装什么、跑什么）
- **docker-compose.yml**：一张"怎么把多个箱子连起来"的拼装图（后端 + 数据库 + 模型服务）

---

## 三、Day 29 详细步骤：创建 FastAPI 后端 `app.py`

### 步骤 1：创建文件

```powershell
New-Item -Path "E:\finrag\FinRAG\app.py" -ItemType File -Force
```

### 步骤 2：粘贴完整代码

```python
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

### 步骤 3：运行后端服务

> ⚠️ 先设 HF 镜像（新终端）：
>
> ```powershell
> $env:HF_ENDPOINT = "https://hf-mirror.com"
> ```

```powershell
python app.py
```

**第一次运行要加载模型**（约 1-2 分钟），看到下面这行就成功了：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 步骤 4：打开 Swagger 文档（导师检查点）

在浏览器地址栏输入：

```
http://127.0.0.1:8000/docs
```

你会看到 FastAPI 自动生成的蓝色接口文档页面——列出 `/health`、`/query`、`/agent_query` 三个接口，每个都能点开"**Try it out**"直接测试。

**测试步骤**：

1. 点 `/health` → Try it out → Execute → 应该看到 `{"status": "ok", ...}`
2. 点 `/query` → Try it out → Request body 填：


   ```json
   {"question": "宁德时代的主营业务是什么"}
   ```
   → Execute → 应该返回答案和引用
3. 点 `/agent_query` → 填：
   ```json
   {"question": "宁德时代今天股价多少"}
   ```
   → Execute → 应该返回行情（本地演示数据）

✅ **Swagger 文档可访问 + 3 个接口都通 = Day 29 完成！** 截图发我。

---

## 四、Day 30 详细步骤：写 Docker 文件（交付物）

> ⚠️ **务实说明**：你的电脑没装 Docker Desktop，装它需要下载几百 MB + WSL2 + 重启，且国内拉镜像常出问题。  
> **Day 30 我们先把 Dockerfile + docker-compose.yml 写好**（面试交付物），部署测试列为**可选**（网络允许再装 Docker）。

### 步骤 1：创建 Dockerfile

```powershell
New-Item -Path "E:\finrag\FinRAG\Dockerfile" -ItemType File -Force
```

粘贴：

```dockerfile
# FinRAG 后端镜像
FROM python:3.11-slim

WORKDIR /app

# 系统依赖（Chromadb 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动 FastAPI
CMD ["python", "app.py"]
```

### 步骤 2：创建 docker-compose.yml

```powershell
New-Item -Path "E:\finrag\FinRAG\docker-compose.yml" -ItemType File -Force
```

粘贴：

```yaml
# FinRAG 一键启动
version: "3.8"

services:
  backend:
    build: .
    container_name: finrag-backend
    ports:
      - "8000:8000"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - HF_ENDPOINT=https://hf-mirror.com
    volumes:
      - ./data:/app/data          # 数据卷（向量库不丢）
    restart: unless-stopped

  # 说明：本地 Ollama（INT4）服务占位。
  # 安装 Docker 且网络允许后可启用：
  # ollama:
  #   image: ollama/ollama
  #   container_name: finrag-ollama
  #   ports:
  #     - "11434:11434"
  #   volumes:
  #     - ollama_data:/root/.ollama
  # volumes:
  #   ollama_data:
```

### 步骤 3：给 .gitignore 加 Docker 相关排除（可选）

```powershell
echo "data/vector_db/" >> .gitignore
```

### 步骤 4：提交

```powershell
git add app.py Dockerfile docker-compose.yml
git commit -m "feat: Day29-30 FastAPI后端（/health /query /agent_query + Swagger）+ Docker化配置"
git tag -a v0.6.0 -m "FastAPI后端 + Docker部署配置"
```

---

## 五、面试话术

**Q: 你的系统怎么给别人用？**

> "我封装了 FastAPI 后端，三个接口：/health 健康检查、/query 研报问答（RAG）、/agent_query 实时数据（Agent）。FastAPI 自动生成 Swagger 文档，任何人打开 /docs 就能测试。接口层和核心系统解耦，前端、移动端、其他服务都能调用。"

**Q: 怎么做工程化部署？**

> "我写了 Dockerfile 和 docker-compose.yml：后端 + 向量库数据卷一键启动，本地 Ollama 模型服务也预留了占位。容器化后系统环境完全隔离，换台机器也能跑。"

**Q: FastAPI 比 Flask 好在哪？**

> "FastAPI 基于 Pydantic 自动做请求校验和文档生成，自带 Swagger UI 和交互式测试，性能上支持异步。对演示项目来说，Swagger 文档就是最好的'使用说明书'——面试官打开就能自己试。"

---

## 六、常见问题排错

| 现象                                               | 原因                | 解决                                                                         |
| ------------------------------------------------ | ----------------- | -------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'fastapi'` | 没装                | `pip install fastapi uvicorn -i https://pypi.tuna.tsinghua.edu.cn/simple/` |
| 浏览器打不开 /docs                                     | 服务没跑起来            | 回 PowerShell 看有没有报错；确认看到 `Uvicorn running`                                 |
| /query 返回 500                                    | 模型没加载完            | 等第一次加载完成（约1-2分钟）再测试                                                        |
| /agent_query 返回 503                              | rag_agent 导入失败    | 看启动日志里的 warning；确认 rag_agent.py 语法正确                                       |
| 端口被占用                                            | 8000 被别的程序占       | 改 `uvicorn.run(app, host="127.0.0.1", port=8001)`                          |
| Docker 命令不存在                                     | 没装 Docker Desktop | 可选步骤，不影响交付物完成                                                              |

---

## 七、验收清单（对照导师检查点）

- [ ] Day 29：`python app.py` 启动成功，看到 `Uvicorn running`
- [ ] Day 29：浏览器打开 `http://127.0.0.1:8000/docs`（Swagger 文档可访问 ✅）
- [ ] Day 29：/health、/query、/agent_query 三个接口测试通过
- [ ] Day 30：Dockerfile + docker-compose.yml 已创建
- [ ] Day 30：commit + tag v0.6.0
- [ ] （可选）安装 Docker Desktop 后跑 `docker-compose up`

---

## 八、第 5 周预告

- Day 31-32：Gradio 完整界面（PDF 上传 + 引用展示 + Agent 工具可视化）+ GitHub Release v1.0.0
- Day 33-34：双模式对比（需装 Ollama + qwen2.5:7b）+ 论文准备
- Day 35：录制 3-5 分钟 Demo 视频（上传研报 → 问答 → 引用 → 数值推理 → Agent 查数据 → 双模式）
