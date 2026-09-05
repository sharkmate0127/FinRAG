# Day 31-32 小白操作指南：Gradio 完整界面 + GitHub Release v1.0.0

> 日期：2026-08-28 ｜ 项目：FinRAG v3.0 ｜ 导师方案：Day 33-34（第 5 周收官）
> 你的 API 已切换 **DeepSeek**，代码沿用已验证配置。

---

## 一、先看导师要求（PDF 原文摘录）

### Day 33-34：Gradio 界面
- Gradio 前端开发
- 支持 PDF 上传 + 对话区域 + 引用展示 + Agent 工具调用可视化
- 美化界面，添加使用说明
- **GitHub Release：v1.0.0**
- 检查点：从上传 PDF 到问答全流程流畅

### 你的环境现状（我查过了）
| 项目 | 状态 |
|---|---|
| gradio | ✅ 已装（6.23.1） |
| app_gradio.py | 只有 18 行（Day 3 的 Hello World） |
| git | 已 commit 到 Day 29-30，tag v0.6.0 |

**所以 Day 31-32 任务**：把 18 行的 Hello World 升级成**完整可用的金融问答界面**。

---

## 二、核心概念解释（零基础版）

### 1. Gradio 是什么？
大白话：**Python 一键生成网页界面的工具**。写 20 行代码就有一个能点的网页。
类比：FastAPI 是"给程序员的 API 接口"（命令行/代码用），Gradio 是"给普通人的网页界面"（鼠标点一点就能用）。

### 2. 界面包含哪几块？
| 模块 | 作用 | 对应你系统的能力 |
|---|---|---|
| PDF 上传区 | 用户上传研报 | （说明用——你的知识库已内置 21 份研报） |
| 对话区 | 输入问题、看回答 | ask.py / rag_agent.py |
| 引用展示区 | 显示回答引用了哪份研报 | 引用溯源 |
| 工具调用可视化 | 显示 LLM 调了哪个工具 | Agent 能力展示 |

### 3. GitHub Release 是什么？
大白话：给你的项目**发一个正式版本号**（v1.0.0），带说明和附件。
类比：游戏发布正式版——之前都是测试版，现在"正式上线"。面试官点开 Release 就能看到完整成果。

---

## 三、Day 31 详细步骤：升级 `app_gradio.py` 为完整界面

### 步骤 1：备份旧文件（重要）

```powershell
Copy-Item "E:\finrag\FinRAG\app_gradio.py" "E:\finrag\FinRAG\app_gradio_hello_backup.py"
```

### 步骤 2：覆盖 app_gradio.py（完整代码）

```powershell
New-Item -Path "E:\finrag\FinRAG\app_gradio.py" -ItemType File -Force
```

粘贴下面全部内容：

```python
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

    history.append((question, answer))
    return history, cite_text, tool_note


# ===== 构建界面 =====
with gr.Blocks(title="FinRAG 金融研报智能问答", theme=gr.themes.Soft()) as demo:
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
    demo.launch()
```

### 步骤 3：运行界面

> ⚠️ 新终端先设 HF 镜像：
> ```powershell
> $env:HF_ENDPOINT = "https://hf-mirror.com"
> ```

```powershell
python app_gradio.py
```

**第一次运行加载模型约 1-2 分钟**，看到下面这行就成功：

```
Running on local URL:  http://127.0.0.1:7860
```

### 步骤 4：在浏览器测试

自动弹出浏览器（或手动打开）：

```
http://127.0.0.1:7860
```

**测试 3 个场景**（对应导师检查点"从上传 PDF 到问答全流程流畅"——你的知识库已内置 21 份研报，所以直接问答即可）：

| 测试 | 模式 | 输入 | 预期 |
|---|---|---|---|
| ①研报问答 | rag | 宁德时代的主营业务是什么 | 回答 + 引用来源列表 |
| ②实时行情 | agent | 宁德时代今天股价多少 | 行情回答（本地演示数据） |
| ③综合对比 | agent | 研报说宁德时代营收增长20%，实际是多少 | 对比分析 |

✅ **界面能聊、引用能看、工具能跑 = Day 31 完成！** 截图发我。

---

## 四、Day 32 详细步骤：GitHub Release v1.0.0

### 步骤 1：提交代码

```powershell
git add app_gradio.py
git commit -m "feat: Day31-32 Gradio完整界面（对话+引用+工具可视化）+ Release v1.0.0"
```

### 步骤 2：打正式版 Tag

```powershell
git tag -a v1.0.0 -m "FinRAG v1.0.0 正式版：RAG+Agent+评估+部署全链路完成"
```

### 步骤 3：推送到 GitHub（需网络）

```powershell
git push origin main
git push origin v1.0.0
```

> ⚠️ 如果 push 超时（GitHub 443 阻塞）：**连手机热点**再推，或多次重试。

### 步骤 4：创建 GitHub Release（网页操作）

1. 浏览器打开 GitHub 仓库：`https://github.com/sharkmate0127/FinRAG`
2. 点右侧 **Releases** → **Create a new release**
3. 填写：
   - **Tag**: `v1.0.0`（选择已有 tag）
   - **Title**: `FinRAG v1.0.0 - 金融研报智能问答系统`
   - **内容**（复制粘贴）：
     ```
     ## FinRAG v1.0.0 正式版

     基于 RAG + Agent 双架构的金融研报智能问答系统。

     ### 核心能力
     - 研报问答（RAG）：混合检索+重排，引用溯源，数值推理
     - Agent 工具调用：LLM 自主决定调股价/财务工具
     - RAG+Agent 协同：研报预测 vs 实际数据综合对比
     - 多轮对话：滑动窗口 + 追问增强

     ### 量化结果
     - 检索 Hit Rate 100%，MRR 1.000
     - 路由准确率 100%
     - RAGAS Answer Relevancy 0.798
     - Prompt 优化 +48.6%

     ### 使用
     ```bash
     pip install -r requirements.txt
     python app_gradio.py   # Web 界面
     python app.py          # FastAPI 后端（Swagger: /docs）
     ```
     ```
4. 点 **Publish release**

---

## 五、面试话术

**Q: 你的项目怎么演示？**

> "我的系统有完整的 Web 界面：打开 Gradio 页面就能直接问答。研报内容问题带引用溯源（显示引用了哪份研报哪段），实时数据问题走 Agent 工具调用，混合问题两边协同对比。整个流程从提问到回答到引用展示，5 分钟能演示完。"

**Q: 工程化方面做了什么？**

> "FastAPI 后端提供 /query /agent_query /health 接口，Swagger 自动生成文档；Dockerfile 和 docker-compose.yml 实现容器化；GitHub 发布了 v1.0.0 Release，包含完整的 README、架构说明和量化评估结果。"

**Q: 为什么不直接用 FastAPI 而用 Gradio？**

> "两者定位不同：FastAPI 是给开发者调用的 REST API，Gradio 是给最终用户的可视化界面。面试或汇报时用 Gradio 演示更直观；生产集成时用 FastAPI。我的系统两者都有。"

---

## 六、常见问题排错

| 现象 | 原因 | 解决 |
|---|---|---|
| `Running on local URL` 没出现 | 模型还在加载 | 等 1-2 分钟 |
| 浏览器打开 7860 白屏 | 服务没起来 | 回 PowerShell 看报错 |
| 输入问题没反应 | 网络/API 问题 | 看 PowerShell 报错截图发我 |
| `smart_answer` 未定义 | rag_agent 导入失败 | 看启动日志 warning，确认 rag_agent.py 语法 |
| 端口被占用 | 7860 被占用 | 改 `demo.launch(server_port=7861)` |
| push 超时 | GitHub 443 阻塞 | 连手机热点 / 多次重试 / 只 commit 留本地 |

---

## 七、验收清单（对照导师检查点）

- [ ] Day 31：Gradio 界面打开，`http://127.0.0.1:7860` 可访问
- [ ] Day 31：3 个场景测试通过（研报问答 / 实时行情 / 综合对比）
- [ ] Day 31：引用来源区能显示研报来源
- [ ] Day 32：commit + tag v1.0.0
- [ ] Day 32：GitHub Release 发布成功（网络允许时）

---

## 八、第 6 周预告（论文 + 面试准备）

- Day 1-2：论文第一章（引言：选题背景、问题定义、研究意义）
- Day 3：论文第二章（相关工作：RAG 演进、金融 NLP）
- Day 4：论文第三章（系统设计：架构图、RAG 算法、Prompt 策略）
- Day 5：GitHub 仓库优化（README 完善、License、注释检查）
- Day 6：面试准备（简历更新、5 分钟项目介绍、STAR 话术）
- Day 7：收尾（项目复盘 + 论文初稿 + 最终 Release）
