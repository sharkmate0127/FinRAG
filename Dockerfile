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
