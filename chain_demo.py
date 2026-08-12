# -*- coding: utf-8 -*-
"""第一个 LangChain Chain：模板 → 模型 → 输出"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os  # ← 加这一行

load_dotenv()

llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),  # ← 加这一行（关键修复）
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    temperature=0.3,
)

template = PromptTemplate.from_template(
    "你是一名金融研究助手。请用中文、简洁地回答问题。\n问题：{question}"
)

chain = template | llm | StrOutputParser()

answer = chain.invoke({"question": "什么是 RAG？"})
print("LangChain 回答：", answer)
