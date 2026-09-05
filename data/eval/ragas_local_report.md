# FinRAG RAGAS 评估报告（local 通道）

- 日期：2026-09-05
- 通道：Qwen2.5-7B INT4（本地 Ollama）
- 评测集：71 题
- 评估器（judge）：DeepSeek（deepseek-chat），裁判中立
- Embedding：bge-large-zh-v1.5（本地）

## 指标结果

| 指标 | 得分 | 方案目标 | 是否达标 |
|---|---|---|---|
| Faithfulness | 1.000 | >0.70 | ✅ |
| Answer Relevancy | 0.873 | >0.75 | ✅ |
| Context Precision | 0.909 | >0.65 | ✅ |
| Context Recall | 0.556 | >0.60 | ❌ |
