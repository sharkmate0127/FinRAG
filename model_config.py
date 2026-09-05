# -*- coding: utf-8 -*-
"""model_config.py - FinRAG 双模型配置中心"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_model_mode() -> str:
    """读取模型模式；默认使用 DeepSeek API"""
    mode = os.getenv("FINRAG_MODEL_MODE", "api").lower().strip()
    if mode not in {"api", "local"}:
        raise ValueError("FINRAG_MODEL_MODE 必须是 api 或 local")
    return mode


def build_llm():
    """统一构造 DeepSeek 或 Qwen Ollama LLM"""
    mode = get_model_mode()

    if mode == "local":
        return ChatOpenAI(
            api_key="ollama",
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
            temperature=0.2,
        )

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("FINRAG_MODEL_MODE=api，但没有找到 DEEPSEEK_API_KEY")

    return ChatOpenAI(
        api_key=api_key,
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        temperature=0.2,
    )


def describe_mode() -> str:
    """返回当前模式的可读说明"""
    if get_model_mode() == "local":
        return "local / Ollama / Qwen2.5-7B"
    return "api / DeepSeek / deepseek-chat"
