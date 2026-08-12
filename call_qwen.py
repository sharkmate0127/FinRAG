# -*- coding: utf-8 -*-
"""第一个 DeepSeek API 调用：问什么答什么"""
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  # 读取 .env 里的 API Key

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是 FinRAG 的金融研究助手。"},
        {"role": "user", "content": "用一句话介绍什么是 RAG？"},
    ],
)

print("模型回答：", response.choices[0].message.content)
