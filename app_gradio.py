# -*- coding: utf-8 -*-
"""Gradio 入门：一个最简单的问答界面"""
import gradio as gr

def respond(question: str):
    # 第 3 周会把这里换成真正的 RAG 回答
    return f"收到问题：{question}\n（这是环境测试回复，RAG 功能第 3 周接入）"

demo = gr.Interface(
    fn=respond,
    inputs=gr.Textbox(label="你的问题"),
    outputs=gr.Textbox(label="回答"),
    title="FinRAG 环境测试",
    description="上传研报问答功能即将上线",
)

if __name__ == "__main__":
    demo.launch()
