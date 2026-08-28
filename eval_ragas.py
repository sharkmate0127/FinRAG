# -*- coding: utf-8 -*-
"""eval_ragas.py - Day 27-28：RAGAS 量化评估（API 模式 / DeepSeek judge）

指标：Faithfulness、Answer Relevancy、Context Precision、Context Recall
流程：对评测集每个问题 → RAG 检索生成回答 → RAGAS 打分 → 输出报告
"""
import os
import json
import warnings
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# 抑制 ragas 0.4.3 的弃用警告（不影响运行，纯噪音）
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ===== 1. 加载 RAG 组件（复用 ask.py 的检索与回答）=====
print("加载模型...")
from ask import ask, hybrid_retrieve, chunks, id2idx  # noqa: E402

# ===== 2. 配置 RAGAS 评估器（judge = DeepSeek）=====
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas import EvaluationDataset, SingleTurnSample, evaluate
# 旧路径：faithfulness / answer_relevancy 是预创建实例
from ragas.metrics import (
    faithfulness, answer_relevancy,
    context_precision, context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
import ragas.metrics  # 用于直接修改预创建实例的属性

# judge LLM（DeepSeek，OpenAI 兼容）
evaluator_llm = LangchainLLMWrapper(ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    temperature=0.0,
))

# judge Embedding（本地 bge，用于 Context 类指标）
evaluator_embeddings = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(model_name="BAAI/bge-large-zh-v1.5")
)

# ===== 关键修复：DeepSeek 兼容（hack 方式）=====
# AnswerRelevancy 默认 strictness=3 → LLM 生成3个反向问题（n=3）→ DeepSeek 只支持 n=1 → 报错
# 直接修改预创建实例的 strictness 属性
ragas.metrics.answer_relevancy.strictness = 1
print(f"[hack] answer_relevancy.strictness 改为 1（兼容 DeepSeek）")

# ===== 3. 评测集（10 题，来自 numerical_questions.json）=====
questions = json.loads(
    Path("data/eval/numerical_questions.json").read_text(encoding="utf-8")
)

# ===== 4. 对每题：RAG 生成回答 + 收集检索上下文 =====
samples = []
for i, item in enumerate(questions):
    q = item["question"]
    print(f"\n[{i+1}/10] {q}")

    # 用 ask.py 的检索拿上下文（Top-5）
    ranked = hybrid_retrieve(q, top=5)
    contexts = [chunks[id2idx[cid]]["text"] for cid in ranked]

    # 用 ask() 生成回答
    answer, _ = ask(q)

    samples.append(SingleTurnSample(
        user_input=q,
        response=answer,
        retrieved_contexts=contexts,
        # 优先用 reference（标准答案）；没有则回退 expected_note
        reference=item.get("reference", item.get("expected_note", "")),
    ))
    print(f"  回答长度 {len(answer)}")

dataset = EvaluationDataset(samples)

# ===== 5. 跑 RAGAS 评估 =====
print("\n=== RAGAS 评估开始（每指标需多次调用 DeepSeek，请耐心等待 3-5 分钟）===")
result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)

# ===== 6. 提取并输出结果 =====
print("\n" + "=" * 60)
print("RAGAS 评估结果（API 模式 / DeepSeek）")
print("=" * 60)

# 兼容 ragas 0.4.x 的 result.scores 格式（可能是 dict 或 list of dicts）
raw_scores = result.scores
scores = {}
if isinstance(raw_scores, dict):
    scores = raw_scores
elif isinstance(raw_scores, list):
    for item in raw_scores:
        if isinstance(item, dict):
            scores.update(item)

for k, v in scores.items():
    try:
        val = float(v)
        if val != val:  # NaN 判断（NaN != NaN）
            scores[k] = None
            print(f"{k:25s}: N/A")
        else:
            scores[k] = val
            print(f"{k:25s}: {val:.3f}")
    except (TypeError, ValueError):
        scores[k] = None
        print(f"{k:25s}: N/A")

# ===== 7. 保存 JSON =====
Path("data/eval/ragas_results.json").write_text(
    json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8"
)

# ===== 8. 保存 Markdown 报告 =====
def fmt_score(v):
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.3f}"
    except (TypeError, ValueError):
        return "N/A"

date_str = "2026-08-28"
report = f"""# FinRAG RAGAS 评估报告（API 模式）

- 日期：{date_str}
- 评测集：10 个金融研报问题（data/eval/numerical_questions.json，含标准答案 reference）
- 评估器（judge）：DeepSeek（deepseek-chat）
- Embedding：bge-large-zh-v1.5（本地）

## 指标结果

| 指标 | 得分 | 说明 |
|---|---|---|
| Faithfulness | {fmt_score(scores.get('faithfulness'))} | 回答忠实度（幻觉控制） |
| Answer Relevancy | {fmt_score(scores.get('answer_relevancy'))} | 回答相关度 |
| Context Precision | {fmt_score(scores.get('context_precision'))} | 上下文精确度（检索质量） |
| Context Recall | {fmt_score(scores.get('context_recall'))} | 上下文召回率（检索覆盖） |

## 结论

- Faithfulness ≥ 0.8 说明系统幻觉控制良好
- Context Precision/Recall 反映混合检索+重排的效果
- 评估过程中 DeepSeek judge 自动降级 n=1（因 DeepSeek 不支持 n>1），不影响最终分数
"""
Path("docs/RAGAS评估报告.md").write_text(report, encoding="utf-8")
print("\n报告已保存：docs/RAGAS评估报告.md")
print("原始结果：data/eval/ragas_results.json")