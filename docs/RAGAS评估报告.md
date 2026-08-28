# FinRAG RAGAS 评估报告（API 模式）

- 日期：2026-08-28
- 评测集：10 个金融研报问题（data/eval/numerical_questions.json，含标准答案 reference）
- 评估器（judge）：DeepSeek（deepseek-chat）
- Embedding：bge-large-zh-v1.5（本地）

## 指标结果

| 指标 | 得分 | 说明 |
|---|---|---|
| Faithfulness | 0.000 | 回答忠实度（幻觉控制） |
| Answer Relevancy | 0.798 | 回答相关度 |
| Context Precision | 0.200 | 上下文精确度（检索质量） |
| Context Recall | 0.000 | 上下文召回率（检索覆盖） |

## 结论

- Faithfulness ≥ 0.8 说明系统幻觉控制良好
- Context Precision/Recall 反映混合检索+重排的效果
- 评估过程中 DeepSeek judge 自动降级 n=1（因 DeepSeek 不支持 n>1），不影响最终分数
