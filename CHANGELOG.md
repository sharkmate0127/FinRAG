# Changelog

所有 FinRAG 的版本变更记录。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Planned
- /upload_pdf 接口（FastAPI，支持研报即时入库）
- Gradio 上传 PDF 组件联动

## [1.1.1] - 2026-09-05

### Fixed
- **股价工具东财接口被 IP 风控**（em/push2his 域 RemoteDisconnected）：
  - test_tool.py 升级为**四级降级**：腾讯证券直连 → 新浪财经直连 → akshare → 本地演示
  - 腾讯直连：`https://qt.gtimg.cn/q=sz002594`（GBK，`~` 分隔，无需鉴权）
  - 新浪直连：`https://hq.sinajs.cn/list=sz000001`（需 `Referer: finance.sina.com.cn`）
- 证据生成脚本从 `logs/`（被 .gitignore 整目录排除）迁至 `data/eval/`

### Added
- `data/eval/akshare_real_call_20260905.txt`：实时行情真实接口成功证据（腾讯证券官方接口，比亚迪 002594 实价）
- `data/eval/gen_akshare_evidence.py`：可复现的证据生成脚本（腾讯 → 新浪 → 东财兜底，自动重试）

## [1.1.0] - 2026-09-05

### Added
- 双通道 RAGAS 评估（DeepSeek API + Qwen2.5-7B INT4），71 题评测集
- 检索层 top_k 参数扫描（5/8/10），定稿 top=8
- eval_ragas_dual.py 支持断点缓存（防 judge 断网丢答案）
- ask.py 设备开关 `FINRAG_EMB_DEVICE`（local 模式防 8GB 显存撞车）

### Changed
- 评测集从 10 题纯数值扩到 71 题混合类型（factual 46 / numerical 10 / agent 7 / comparison 4 / reasoning 4）
- .gitignore 重写为干净 UTF-8（修复 UTF-16 碎片导致忽略规则失效的隐患）

### Docs
- 增补 docs/RAGAS_双通道评估报告_论文版.md（论文实验章素材）
- 增补 docs/消融实验汇总表.md（论文实验章主表）
- 增补 docs/论文三章提纲.md、Demo演示脚本_分镜.md

## [1.0.0] - 2026-08-31

### Added
- FastAPI 后端（/health /query /agent_query）
- Gradio 界面（127.0.0.1:7860）
- Docker 配置（Dockerfile + docker-compose.yml）
- RAGAS 评估初版（Faithfulness / Answer Relevancy / Context Precision / Context Recall）
- Agent 工具调用（get_stock_price / get_financial_data，三级降级）
- 引用溯源增强（v0.3，每个回答标注来源 PDF + 段落）

## [0.5.0] - 2026-08-15

### Added
- 检索质量优化 v0.5：Hit Rate 100%，混合检索 + Reranker，MRR 1.000

## [0.4.0] - 2026-08-10

### Added
- 数值推理增强 v0.4：Few-Shot，评测准确率 70%

## [0.3.0] - 2026-08-05

### Added
- 引用溯源增强 v0.3：编号引用 + 验证脚本

## [0.2.0] - 2026-07-25

### Added
- Prompt 工程 A/B 测试，ask.py v0.2，P3 模板胜出（+48.6%）

## [0.1.0] - 2026-07-10

### Added
- RAG 核心管线 v0.1（LangChain LCEL + bge-large-zh-v1.5 + ChromaDB）

[Unreleased]: https://github.com/sharkmate0127/FinRAG/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/sharkmate0127/FinRAG/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/sharkmate0127/FinRAG/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/sharkmate0127/FinRAG/releases/tag/v1.0.0
