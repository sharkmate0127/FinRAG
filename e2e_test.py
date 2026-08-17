# -*- coding: utf-8 -*-
"""端到端全量测试：跑数值评测集 + 检索测试集，输出全部回答供人工检查"""
import json
from pathlib import Path
from ask import ask, history  # 复用 v0.6 的 ask（注意：ask.py 有交互式主循环，先注释掉）

# 注意：如果 ask.py 的 if __name__ == "__main__" 段会拦截，
# 请把 ask.py 主循环段删除或注释后再跑本脚本

questions = [
    # 数值类（Day 16 评测集）
    "宁德时代2024年的预测营收是多少",
    "比亚迪2026年的归母净利润预测是多少",
    "拓普集团2025年的归母净利润预测是多少",
    "比亚迪2025年净利润相比2024年预测增长了多少",
    # 事实/推理类
    "宁德时代的主营业务是什么",
    "宁德时代的成长驱动因素有哪些",
    "比亚迪出海战略的进展如何",
    # 对比类
    "宁德时代和比亚迪的营收规模对比",
    # 越界类（应拒绝）
    "预测一下宁德时代明天的股价",
]

os_results = []
for q in questions:
    try:
        answer, cited = ask(q)
        os_results.append({"question": q, "answer": answer,
                           "sources": [c["source_file"] for c in cited]})
        print(f"✅ {q[:20]}... 回答长度{len(answer)}")
    except Exception as e:
        os_results.append({"question": q, "answer": f"ERROR: {e}", "sources": []})
        print(f"❌ {q[:20]}... 出错: {e}")

Path("data/eval/e2e_results.json").write_text(
    json.dumps(os_results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n端到端测试完成！结果: data/eval/e2e_results.json")
