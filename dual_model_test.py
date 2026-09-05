# -*- coding: utf-8 -*-
"""dual_model_test.py - DeepSeek API / Qwen Ollama 双模式最小冒烟测试

用法（PowerShell，.venv 已激活）：

    # 1. 测试云端 DeepSeek
    $env:FINRAG_MODEL_MODE = "api"
    python dual_model_test.py

    # 2. 测试本地 Qwen (Ollama)
    $env:FINRAG_MODEL_MODE = "local"
    python dual_model_test.py

依赖：model_config.py 必须与本文件位于同一目录 E:\\finrag\\FinRAG\\
"""

from dotenv import load_dotenv

from model_config import build_llm, describe_mode


def main() -> None:
    """驱动一次最小问询，把模型层验证清楚。"""
    print("当前模型配置:", describe_mode())

    llm = build_llm()  # 由 FINRAG_MODEL_MODE 决定走 api 还是 local

    prompt = "用一句话解释 RAG（检索增强生成）"
    print(">>> 正在调用模型...")
    response = llm.invoke(prompt)

    print("<<< 模型回答:")
    print(response.content)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - 一次性脚本，捕获所有便于排错
        print(f"调用失败: {type(exc).__name__}: {exc}")
        raise
