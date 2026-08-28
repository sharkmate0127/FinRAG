# -*- coding: utf-8 -*-
"""app_gradio.py - Day 31-32：FinRAG 完整 Web 界面

功能：
- 对话区：研报问答（RAG）与实时数据（Agent）双模式
- 引用展示：回答下方列出引用来源研报
- 工具调用可视化：显示 LLM 是否调用了工具
- 使用说明：内置提示
"""
import os
import sys
import traceback
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

# ===== 导入核心系统（复用已有模块）=====
print("加载模型（首次运行需下载，请等待）...")
import ask  # RAG 问答模块
from ask import ask as ask_rag  # 重命名避免冲突

# 尝试加载 Agent 协同系统（失败则只用 RAG）
try:
    from rag_agent import smart_answer
    HAS_AGENT = True
except Exception as e:
    print(f"[warn] rag_agent 导入失败（仅 RAG 模式）: {e}")
    HAS_AGENT = False


def chat(question: str, mode: str, history):
    """核心对话函数（Gradio 回调）

    Args:
        question: 用户问题
        mode: "rag"（研报问答）或 "agent"（协同问答）
        history: Gradio 自动维护的对话历史
    Returns:
        (history, 引用文本, 工具调用说明)
    """
    history = history or []
    if not question.strip():
        return history, "（无输入）", ""

    tool_note = ""
    try:
        if mode == "agent" and HAS_AGENT:
            # Agent 协同模式
            answer = smart_answer(question)
            tool_note = "✅ Agent 已调度（含工具调用/路由分诊）"
            cite_text = "（协同模式：回答含研报引用与实时数据对比）"
        else:
            # RAG 模式
            answer, cited = ask_rag(question)
            if cited:
                cite_text = "引用来源：\n" + "\n".join(
                    f"- [{c['number']}] {c['source_file']}\n  原文: {c['chunk_preview']}..."
                    for c in cited
                )
            else:
                cite_text = "（本次回答未引用具体研报）"
            tool_note = "📚 RAG 模式（检索研报知识库）"
    except Exception as e:
        answer = f"抱歉，处理时出错：{type(e).__name__}: {e}"
        cite_text = ""
        tool_note = f"❌ 出错（{type(e).__name__}）"

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    return history, cite_text, tool_note


# ===== 构建界面 =====
with gr.Blocks(title="FinRAG 金融研报智能问答") as demo:
    gr.Markdown(
        """
# 📈 FinRAG 金融研报智能问答系统

基于 **RAG + Agent** 双架构的金融研报问答系统。
支持研报内容问答（带引用溯源）与实时数据查询（工具调用）。

**快速上手**：
- 问研报内容：`宁德时代的主营业务是什么？`
- 问实时行情：`宁德时代今天股价多少？`
- 问对比分析：`研报说宁德时代营收增长20%，实际是多少？`
        """
    )

    mode = gr.Radio(
        choices=["rag", "agent"],
        value="rag",
        label="问答模式",
        info="rag=研报问答（RAG） / agent=协同问答（RAG+Agent）",
    )

    chatbot = gr.Chatbot(label="对话区域", height=400)
    question = gr.Textbox(
        label="输入你的问题",
        placeholder="例如：宁德时代的主营业务是什么？",
        lines=2,
    )
    submit_btn = gr.Button("发送", variant="primary")

    cite_out = gr.Textbox(label="引用来源", lines=4, interactive=False)
    tool_out = gr.Textbox(label="模式/工具调用", lines=1, interactive=False)

    # 绑定事件
    submit_btn.click(
        chat,
        inputs=[question, mode, chatbot],
        outputs=[chatbot, cite_out, tool_out],
    )
    question.submit(
        chat,
        inputs=[question, mode, chatbot],
        outputs=[chatbot, cite_out, tool_out],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
