# -*- coding: utf-8 -*-
"""eval_ragas_dual.py - 双通道 RAGAS 对比评估（v3.1 核心任务）

用法（PowerShell，.venv 已激活）：
    $env:FINRAG_MODEL_MODE = "api"     # 或 local
    python eval_ragas_dual.py

输出：
    data/eval/ragas_{mode}_results.json
    data/eval/ragas_{mode}_report.md
"""
import os
import json
import warnings
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ===== 1. 确定当前通道 =====
MODE = os.getenv("FINRAG_MODEL_MODE", "api").lower().strip()
print(f"===== 当前通道：{MODE} =====")

# ===== 2. 加载 RAG 组件（ask.py 会自动跟随 FINRAG_MODEL_MODE）=====
print("正在加载模型（bge embedding + reranker + 分词器），约需 1-2 分钟，请耐心等待，勿按 Ctrl+C ...", flush=True)
from ask import ask, hybrid_retrieve, chunks, id2idx  # noqa: E402
print("模型加载完成。", flush=True)

# ===== 3. 配置 RAGAS 评估器（judge 固定用 DeepSeek，保证裁判中立）=====
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import (
    faithfulness, answer_relevancy,
    context_precision, context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
import ragas.metrics

evaluator_llm = LangchainLLMWrapper(ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    temperature=0.0,
))
evaluator_embeddings = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(model_name="BAAI/bge-large-zh-v1.5")
)

# DeepSeek 兼容修复（同 eval_ragas.py）
ragas.metrics.answer_relevancy.strictness = 1
print("[hack] answer_relevancy.strictness 改为 1（兼容 DeepSeek）")

# ===== 4. 评测集（优先级：71 题最终版 → 50 题扩充版 → 10 题原始数值题）=====
eval_path = None
for cand in ("qa_pairs_71_final.json", "qa_pairs_50.json", "numerical_questions.json"):
    p = Path(f"data/eval/{cand}")
    if p.exists():
        eval_path = p
        if cand != "qa_pairs_71_final.json":
            print(f"[提示] 未找到 qa_pairs_71_final.json，回退用 {cand}")
        break
if eval_path is None:
    raise FileNotFoundError("data/eval/ 下未找到任何评测集 JSON，请先生成 qa_pairs_71_final.json")
questions = json.loads(eval_path.read_text(encoding="utf-8"))
print(f"评测集：{eval_path.name}，共 {len(questions)} 题")

# ===== 5. 对每题：RAG 生成回答 + 收集检索上下文（带断点缓存，防断网白跑）=====
CACHE_PATH = Path(f"data/eval/cache_samples_{MODE}.json")

def _build_sample_dict(i, item):
    q = item["question"]
    print(f"\n[{i+1}/{len(questions)}] {q}")
    ranked = hybrid_retrieve(q, top=8)
    contexts = [chunks[id2idx[cid]]["text"] for cid in ranked]
    answer, _ = ask(q)
    return {
        "user_input": q,
        "response": answer,
        "retrieved_contexts": contexts,
        "reference": item.get("reference", item.get("expected_note", "")),
    }

# 优先复用已生成的回答缓存（judge 阶段断网/失败后重跑可跳过 40-60 分钟的生成）
samples = []
if CACHE_PATH.exists():
    cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    if len(cached) == len(questions):
        print(f"[断点续跑] 命中 {len(cached)} 份回答缓存（{CACHE_PATH.name}），跳过生成阶段，直接评估")
        samples = [SingleTurnSample(**d) for d in cached]
    else:
        print(f"[提示] 缓存题数 {len(cached)} 与评测集 {len(questions)} 不符，重新生成")
if not samples:
    sample_dicts = []
    for i, item in enumerate(questions):
        sample_dicts.append(_build_sample_dict(i, item))
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(sample_dicts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[缓存] {len(sample_dicts)} 份回答已存盘：{CACHE_PATH.name}（下次断网重跑可跳过生成阶段）")
    samples = [SingleTurnSample(**d) for d in sample_dicts]

dataset = EvaluationDataset(samples)

# ===== 6. 跑 RAGAS 评估 =====
print(f"\n=== RAGAS 评估开始（{MODE} 通道，约 3-5 分钟）===")
result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)

# ===== 7. 提取结果 =====
print("\n" + "=" * 60)
print(f"RAGAS 评估结果（{MODE} 通道）")
print("=" * 60)
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
        scores[k] = None if val != val else val
        print(f"{k:25s}: {val:.3f}" if val == val else f"{k:25s}: N/A")
    except (TypeError, ValueError):
        scores[k] = None
        print(f"{k:25s}: N/A")

# ===== 8. 保存结果 =====
scores["mode"] = MODE
scores["n_questions"] = len(questions)
out_json = Path(f"data/eval/ragas_{MODE}_results.json")
out_json.write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n结果已保存：{out_json}")

def fmt(v):
    return "N/A" if v is None else f"{float(v):.3f}"

report = f"""# FinRAG RAGAS 评估报告（{MODE} 通道）

- 日期：{__import__('datetime').date.today().isoformat()}
- 通道：{'DeepSeek API（云端）' if MODE == 'api' else 'Qwen2.5-7B INT4（本地 Ollama）'}
- 评测集：{len(questions)} 题
- 评估器（judge）：DeepSeek（deepseek-chat），裁判中立
- Embedding：bge-large-zh-v1.5（本地）

## 指标结果

| 指标 | 得分 | 方案目标 | 是否达标 |
|---|---|---|---|
| Faithfulness | {fmt(scores.get('faithfulness'))} | >0.70 | {'✅' if (scores.get('faithfulness') or 0) > 0.70 else '❌'} |
| Answer Relevancy | {fmt(scores.get('answer_relevancy'))} | >0.75 | {'✅' if (scores.get('answer_relevancy') or 0) > 0.75 else '❌'} |
| Context Precision | {fmt(scores.get('context_precision'))} | >0.65 | {'✅' if (scores.get('context_precision') or 0) > 0.65 else '❌'} |
| Context Recall | {fmt(scores.get('context_recall'))} | >0.60 | {'✅' if (scores.get('context_recall') or 0) > 0.60 else '❌'} |
"""
Path(f"data/eval/ragas_{MODE}_report.md").write_text(report, encoding="utf-8")
print(f"报告已保存：data/eval/ragas_{MODE}_report.md")
