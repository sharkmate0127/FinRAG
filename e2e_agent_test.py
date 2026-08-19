# -*- coding: utf-8 -*-
"""e2e_agent_test.py - Day 26：协同版端到端测试

覆盖 4 类问题：研报类 / 实时类 / 混合类 / 越界类（应拒绝）
输出全部回答供人工检查
"""
import json
from pathlib import Path
from rag_agent import smart_answer, history

questions = [
    # 研报内容类（RAG）
    "宁德时代的主营业务是什么",
    "中科曙光2026年营收预测",
    # 实时数据类（Agent）
    "宁德时代今天股价多少",
    "比亚迪现在的最新价",
    # 混合类（RAG+Agent 协同）
    "研报说宁德时代营收增长20%，实际是多少",
    "比亚迪预测增速和实际增速对比",
    # 越界类（应拒绝或说明局限）
    "预测一下宁德时代明天的股价",
]

results = []
for q in questions:
    try:
        answer = smart_answer(q)
        results.append({"question": q, "answer": answer[:500]})
        print(f"✅ {q[:22]}... 回答长度{len(answer)}")
    except Exception as e:
        results.append({"question": q, "answer": f"ERROR: {e}"})
        print(f"❌ {q[:22]}... 出错: {e}")

Path("data/eval/e2e_agent_results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n端到端测试完成！结果: data/eval/e2e_agent_results.json")
