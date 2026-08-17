# -*- coding: utf-8 -*-
"""agent_demo.py - Day 22 任务：让 DeepSeek LLM 自主决定调工具

核心概念（Agent vs RAG）：
  - RAG: 用户问 → 查知识库 → LLM 看知识库回答（被动）
  - Agent: 用户问 → LLM 自己决定"要不要查、查什么" → 可能调多个工具 → 综合回答（主动）

本脚本演示 OpenAI Function Calling（Tool Use）协议：
  1. 给 LLM 描述"我有一个叫 get_stock_price 的工具，能查股价"
  2. LLM 收到用户问题后，决定要不要调工具
  3. 调的话，LLM 返回 tool_call（工具名 + 参数）
  4. 我们执行工具，把结果回给 LLM
  5. LLM 看结果，组织自然语言答案

面试可讲：
  - Agent = LLM + 工具调用循环
  - 单步决策（一次 tool_call）vs 多步决策（链式工具）
  - 错误处理（工具失败 / LLM 瞎调 / 死循环保护）
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

# ===== 0. 加载 API Key（和项目其他文件保持一致） =====
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 把当前目录加入 path，以便 import test_tool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_tool import get_stock_price

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ===== 1. 工具定义（OpenAI Function Calling 格式） =====
# 这一段就是"告诉 LLM 我有哪些工具，每个工具能干嘛、参数是什么"
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": (
                "查询股票实时价格。支持 A 股（6 位数字代码，如 300750）和港股（5 位数字代码，如 00700）。"
                "返回格式：'宁德时代(300750) 最新价: 250.36 元（数据来源: ...）'。"
                "当用户问某只股票'现在多少钱'、'实时价格'、'今天行情'时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {
                        "type": "string",
                        "description": (
                            "股票代码。例：300750=宁德时代，002594=比亚迪，"
                            "601012=隆基绿能，00700=腾讯港股，688111=金山办公"
                        ),
                    }
                },
                "required": ["stock_code"],
            },
        },
    }
]


# ===== 2. 调用 DeepSeek（HTTP 直连，清晰展示每一步） =====
def call_llm(messages, tools=None):
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"  # 让 LLM 自己决定调不调

    resp = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ===== 3. Agent 主循环：调 LLM → 看是否要调工具 → 调 → 喂回结果 → 再调 LLM =====
def run_agent(user_query: str, max_iter: int = 5) -> str:
    """运行 Agent，处理多轮 tool_calls 直到 LLM 给出最终答案"""
    messages = [
        {
            "role": "system",
            "content": (
                "你是 FinRAG 金融助手，回答要简洁、专业、有数据支撑。"
                "当用户问实时行情时，你必须调用 get_stock_price 工具，"
                "不要凭记忆编造股价。"
            ),
        },
        {"role": "user", "content": user_query},
    ]

    for i in range(max_iter):
        print(f"\n--- 第 {i+1} 轮 LLM 调用 ---")
        result = call_llm(messages, tools=TOOLS)
        msg = result["choices"][0]["message"]

        # 把 LLM 这一轮的回复加入历史
        messages.append(msg)

        # 检查 LLM 是否要调工具
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            print(f"[LLM 决定] 调用 {len(tool_calls)} 个工具")
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                func_args_raw = tc["function"]["arguments"]
                try:
                    func_args = json.loads(func_args_raw)
                except Exception:
                    func_args = {}
                print(f"  -> {func_name}({func_args})")

                # 执行工具
                if func_name == "get_stock_price":
                    tool_result = get_stock_price(func_args.get("stock_code", ""))
                else:
                    tool_result = f"错误：未知工具 {func_name}"

                print(f"  <- 工具返回: {tool_result}")

                # 把工具结果回喂给 LLM（role=tool）
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_result,
                    }
                )
        else:
            # LLM 给了最终答案
            final_answer = msg.get("content", "").strip()
            print(f"[LLM 最终答案] {final_answer}")
            return final_answer

    return f"超过最大迭代次数 {max_iter}，强制退出"


# ===== 4. 测试 3 个不同场景 =====
if __name__ == "__main__":
    if not DEEPSEEK_API_KEY:
        print("ERROR: 请先在 .env 里设置 DEEPSEEK_API_KEY")
        print("示例: DEEPSEEK_API_KEY=sk-xxxxxxxx")
        sys.exit(1)

    test_queries = [
        "宁德时代现在股价多少？",          # 期望 LLM 调 get_stock_price("300750")
        "比亚迪 002594 现在的最新价？",    # 期望 LLM 调 get_stock_price("002594")
        "今天腾讯股价怎么样？",            # 期望 LLM 调 get_stock_price("00700")
    ]

    for q in test_queries:
        print("\n" + "=" * 70)
        print(f"[用户提问] {q}")
        print("=" * 70)
        answer = run_agent(q)
        print(f"\n[最终回答]\n{answer}")
        print()
