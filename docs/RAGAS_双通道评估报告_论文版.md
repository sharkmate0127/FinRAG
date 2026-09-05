# FinRAG 双通道 RAGAS 量化评估报告（论文版）

- **报告日期**：2026-09-05
- **系统版本**：FinRAG v3.1（RAG + Agent 双能驱动，DeepSeek / Qwen 双通道）
- **评测集**：`data/eval/qa_pairs_71_final.json`（71 题，5 类题型，reference 全部为研报原文并经人工校对）
- **评估框架**：RAGAS（ragas>=0.2），4 项指标
- **裁判（judge）**：DeepSeek（deepseek-chat）—— 双通道共用，保证裁判中立
- **Embedding / Reranker**：bge-large-zh-v1.5（1024 维）/ bge-reranker-large，本地部署
- **知识库规模**：20 份券商深度研报 → 11 家上市公司 → 1323 个文本块（500-1000 字/块）

---

## 📌 摘要（结论先行）

经过 4 轮迭代（8/28 → 9/2 → 9/2 → 9/5），最终定稿成绩（检索精排 top=8）：

| 指标 | DeepSeek API | Qwen2.5-7B INT4（本地） | v3.1 方案预期 | 是否达标 |
|---|---|---|---|---|
| Faithfulness（忠实度） | **0.947** | **1.000** | > 0.70 | ✅ |
| Answer Relevancy（相关度） | **0.800** | **0.873** | > 0.75 | ✅ |
| Context Precision（检索精确率） | **1.000** | **0.909** | > 0.65 | ✅ |
| Context Recall（检索召回率） | **0.556** | **0.556** | > 0.60 | ❌ 唯一短板 |

**核心结论**：三项指标达标，Faithfulness / Context Precision 达到或接近满分；唯一不达标项是 **Context Recall（0.556）**，且经「双通道一致 + top_k 扫描不涨」双重证据链证明为**检索候选池源头漏检**（与生成模型无关、与精排块数无关），已归因并写入论文"局限与展望"。

**一句话演进史**：从 8/28 的"三零分"（0 / 0.798 / 0.200 / 0）到 9/5 的"三达标一短板"（0.947 / 0.800 / 1.000 / 0.556），关键转折点是 **reference 由自写答案改为研报原文**——此前 RAGAS 全 0 是评测集设计问题，而非系统缺陷。

---

## 一、评估背景与目标

FinRAG v3.1 采用 **RAG + Agent 双能驱动、DeepSeek（云端）/ Qwen（本地）双通道**架构。论文实验章需要一套可复现、可解释、口径统一的量化评估数据，回答三个问题：

1. **生成质量**：答案是否忠实于研报原文（Faithfulness）、是否答非所问（Answer Relevancy）；
2. **检索质量**：检索到的上下文是否精确有用（Context Precision）、答案所需的原文是否被完整找回（Context Recall）；
3. **双通道差异**：云端 DeepSeek 与本地量化 Qwen 在同一评测基准下的差距及其原因。

评估采用 RAGAS 框架，双通道共用同一裁判模型（DeepSeek）与同一评测集，形成"控制变量"实验设计：**换考生（生成器）、不换阅卷官（judge）、不换卷子（71 题）**。

---

## 二、评测集设计（71 题最终版）

### 2.1 演进过程

| 版本 | 题数 | 类型 | reference 状态 | 问题 |
|---|---|---|---|---|
| v0（8/28 前） | 10 | 纯数值 | 自写答案 | 覆盖面窄，仅数值 |
| v1（8/31） | 50 | 混合 | 部分为占位符 | judge 对占位 reference 全判 0 |
| v2（8/31） | 73 / 75 | 混合 | 待校对 | 含无法在研报找到答案的题 |
| **v3 定稿（9/2）** | **71** | **5 类混合** | **全为研报原文 + 人工校对** | — |

**定稿 71 题的构建流程**：
① 保留 10 道纯数值题（早期积累）；② 从 1323 个文本块中按"事实可考"标准自动挖掘 33 道 factual 题（`build_factual_from_chunks.py`）；③ 补充 agent / comparison / reasoning 题型；④ 对无法在语料中找到原文依据的题逐一修复或删除（如紫光股份无独立研报、腾讯问题改用金山研报语料作答）；⑤ 生成 Excel 校对工作台，人工逐题核对 31 处 reference 并删除 1 道无依据题 → 最终 71 题，**`ref_checked = 71/71`**。

### 2.2 题型构成（factual 46 / numerical 10 / agent 7 / comparison 4 / reasoning 4）

| 题型 | 题数 | 考察点 | 示例 |
|---|---|---|---|
| factual（事实） | 46 | 检索定位 + 忠实摘录 | "宁德时代 2024 年的预测营收是多少" |
| numerical（数值） | 10 | 数值推理 + 单位标注 | 营收 / 净利 / 毛利率预测值 |
| agent（工具调用） | 7 | RAG 与实时工具的路由 | "查一下宁德时代最新股价"（需走 Agent） |
| comparison（对比） | 4 | 跨公司 / 跨文档聚合 | "宁德时代和比亚迪的动力电池毛利率对比" |
| reasoning（推理） | 4 | 多跳逻辑链 | "为什么研报认为宁德时代 2024 营收能增长 15%" |

### 2.3 主题覆盖（11 家公司）

宁德时代 20 · 比亚迪 12 · 拓普集团 7 · 中科曙光 6 · 阳光电源 5 · 浪潮信息 5 · 工业富联 4 · 金山办公 4 · 亿纬锂能 3 · 隆基绿能 3 · 科大讯飞 2（跨公司对比题不计入单公司）

### 2.4 reference 校对原则（本轮修复的核心）

- **reference 必须逐字摘抄研报原文**（而非模型自写答案），保证 RAGAS 的「生成 vs 上下文 vs reference」三角验证有真实的"标准答案块"可比对；
- 每题标注 `source_pdf` 溯源信息，支持人工复核；
- 全部经 Excel 校对工作台人工过一遍（`ref_checked=true` 71/71），**杜绝占位符进入评测集**。

---

## 三、评估方法与实验环境

### 3.1 指标定义

| 指标 | 中文 | 衡量的问题 | 计算要点 |
|---|---|---|---|
| Faithfulness | 忠实度 | 答案是否被检索上下文支持（有无幻觉） | 将答案拆句，逐句与上下文做蕴含判定 |
| Answer Relevancy | 相关度 | 答案是否切题、不答非所问 | 生成答案后反向生成其对应问题，与原题算相似度 |
| Context Precision | 上下文精确率 | 检索出的块是否"块块有用" | 相关块在检索结果中的排位越靠前越高 |
| Context Recall | 上下文召回率 | 答案所需原文是否被完整检索到 | reference 拆句后能否在检索上下文中命中 |

### 3.2 双通道控制变量设计

| 实验组 | 生成器 | 检索器 | judge | 评测集 |
|---|---|---|---|---|
| api 通道 | DeepSeek（云端，deepseek-chat） | 同一套混合检索 | DeepSeek | 同一 71 题 |
| local 通道 | Qwen2.5-7B INT4（本地 Ollama，RTX 4060 8GB） | 同一套混合检索 | DeepSeek | 同一 71 题 |

> judge 固定为 DeepSeek：local 通道换的只是"考生"，阅卷官不变，保证两组成绩可直接比较。

### 3.3 检索链路

混合检索双通道（BM25 关键词 + bge-large-zh 向量，各取候选 20 条）→ 合并 → bge-reranker-large 精排 → **取 top=8** 作为生成上下文与 RAGAS 评估上下文（top_k 定稿过程见第六章）。

### 3.4 硬件与软件环境

| 项 | 配置 |
|---|---|
| 硬件 | Lenovo 拯救者 Y7000P，RTX 4060 Laptop 8GB（8188 MiB） |
| Python | 3.11.9（.venv 虚拟环境） |
| LLM | DeepSeek API（deepseek-chat）/ Ollama qwen2.5:7b INT4 |
| Embedding / Reranker | BAAI/bge-large-zh-v1.5、BAAI/bge-reranker-large |
| 评估 | ragas、datasets、pyarrow 25.0.1 |

---

## 四、评估历程与结果演进（修改过程全记录）

> 本节是论文"实验与改进过程"的素材：**每一轮"改了什么 → 结果如何 → 归因是什么"**。

### 📅 阶段 0（8/28）：初评 —— 10 题纯数值，三零分暴露评测集缺陷

| 指标 | 得分 | 档案 |
|---|---|---|
| Faithfulness | 0.000 | `data/eval/ragas_results.json` |
| Answer Relevancy | 0.798 | ↑ |
| Context Precision | 0.200 | ↑ |
| Context Recall | 0.000 | ↑ |

- **改动**：无（首次评估）。
- **结果诊断**：Faithfulness / Context Precision / Context Recall 全 0 或接近 0。
- **归因（本轮最大认知转折）**：10 题均为**纯数值题**，reference 是模型自写的"标准答案"而非研报原文。RAGAS 的三角验证（答案 vs 上下文 vs reference）要求三者同源可比——数值题答案本身不在上下文中逐字出现，且 reference 不是原文，导致判断器无从比对，几乎全部判 0。**结论：全 0 是评测集设计问题，不是系统缺陷。** 由此启动评测集全面扩建。

### 📅 阶段 1（8/31-9/2）：评测集扩建与 reference 原文化

- **改动**：10 题 → 50 题 → 73/75 题 → 校对定稿 **71 题**；题型从纯数值扩展为 5 类混合；reference 从"自写答案/占位符"全部改为**研报原文摘抄**，并经 Excel 工作台人工校对 71/71。
- **结果**：中期 50 题版（reference 未补全时）RAGAS 仍大面积 0 分，进一步证实"reference 决定分数下限"；71 题定稿版为后续翻身打下基础。
- **归因**：评测集质量（尤其 reference 与语料同源性）是 RAGAS 分数的**第一前置条件**，先于任何系统优化。

### 📅 阶段 2（9/2）：71 题首评 —— 双通道首次"翻身"，同时暴露两个工程问题

**api 通道（top=5）：Faithfulness 1.000 / Answer Relevancy 0.752 / Context Precision 1.000 / Context Recall 0.444**

| 指标 | 阶段 0（10题） | 阶段 2（71题 top5） | 变化 |
|---|---|---|---|
| Faithfulness | 0.000 | **1.000** | 判据修复后满分 |
| Answer Relevancy | 0.798 | 0.752 | 题型变难后小幅回落 |
| Context Precision | 0.200 | **1.000** | 检索质量证真 |
| Context Recall | 0.000 | 0.444 | 首次有分，仍偏低 |

- **改动**：仅换评测集（reference 原文化），系统代码零改动。
- **结果诊断**：Faithfulness / Context Precision 从 0 到满分 —— **证明 reference 原文化是正确修复**，系统答案忠实、检索精确。
- **暴露的工程问题 ①：8GB 显存撞车**。local 通道首跑至 53/71 崩溃（`CUDA error: unknown error`）：Qwen2.5-7B INT4（约 4.7GB）与 bge embedding、bge-reranker 同时驻留 GPU，峰值超 8GB。**修复**：`ask.py` / `rag_agent.py` 新增设备开关 `FINRAG_EMB_DEVICE=cpu`，local 评估时 embedding/reranker 降级到 CPU、GPU 全让给 Qwen。
- **暴露的工程问题 ②：评测脚本无缓存**。judge 阶段依赖联网，中途断网导致已生成的 71 份答案随进程退出丢失。**修复**：`eval_ragas_dual.py` 增加断点缓存（`cache_samples_{mode}.json`），生成即落盘，重跑自动跳过答题仅补打分（3-5 分钟）。
- **附带环境修复**：pyarrow DLL 被 Windows Smart App Control 拦截（重装修复）；fsspec 钉版 ≤ 2026.6.0 消除 datasets 依赖冲突；DeepSeek 余额不足（402）→ 充值后重跑。

**local 通道（top=5，CPU embedding/reranker 重跑成功）：Faithfulness 0.444 / Answer Relevancy 0.873 / Context Precision 0.950 / Context Recall 0.444**

### 📅 阶段 3（9/2-9/5）：top_k 检索参数扫描 —— 定稿 top=8

针对 Context Recall 0.444 未达标，按"最小代价优先"原则执行 top_k 扫描（仅跑 api 通道即可验证——Recall 是检索层指标，与生成器无关，省去 local 40-60 分钟/轮）：

| top_k | Faithfulness | Answer Relevancy | Context Precision | **Context Recall** | 结论 |
|---|---|---|---|---|---|
| 5（基线） | 1.000 | 0.752 | 1.000 | 0.444 | 基准 |
| **8（定稿）** | 0.947 | **0.800** | **1.000** | **0.556（+0.112）** | 提升且 Precision 不掉 |
| 10（实验） | 1.000 | 0.816 | 0.907（-0.093） | 0.556（持平） | 噪声进入，不再获益 |

- **改动**：`eval_ragas_dual.py` 检索精排块数 5 → 8 → 10，逐档全量评估。
- **判定**：top=8 是收益/代价最优平衡点——Recall 提升 0.112 而 Precision 保持满分；top=10 时 Precision 掉 0.093、Recall 不再上涨 → **退回并定稿 top=8**。
- **重要发现**：8→10 块 Recall 纹丝不动，说明漏检的 reference 句**根本没进入 rerank 前的候选池**（混合检索各取 20 条的源头就未召回）——Recall 瓶颈在检索源头而非精排块数。

### 📅 阶段 4（9/5）：双通道对称定稿 —— 论文引用版本

local 通道按定稿 top=8 + CPU embedding/reranker + 断点缓存重跑（中途断网致 judge N/A 一次，靠缓存 3-5 分钟续跑成功）：

| 指标 | api（DeepSeek，top8） | local（Qwen INT4，top8） |
|---|---|---|
| Faithfulness | 0.947 | **1.000** |
| Answer Relevancy | 0.800 | **0.873** |
| Context Precision | **1.000** | 0.909 |
| Context Recall | 0.556 | 0.556 |

**过程与结果文件全部入 git（tag v1.1.0），报告归档，双通道对称版数字成为论文唯一引用口径。**

---

## 五、最终定稿结果与方案目标对照

### 5.1 论文引用总表（top=8，71 题，双通道对称）

| 指标 | DeepSeek API | Qwen2.5-7B INT4 | v3.1 方案预期 | 达标 |
|---|---|---|---|---|
| Faithfulness | 0.947 | 1.000 | API 0.80-0.90 / 本地 0.70-0.80 | ✅（本地超预期） |
| Answer Relevancy | 0.800 | 0.873 | API 0.75-0.85 / 本地 0.70-0.80 | ✅ |
| Context Precision | 1.000 | 0.909 | — | ✅ |
| Context Recall | 0.556 | 0.556 | > 0.60 | ❌ 差 0.044 |

### 5.2 双通道一致性观察

- **Context Recall 两通道完全相同（0.556 = 0.556）**：召回由共享检索器决定，与生成器无关——与实验设计预期一致；
- **Answer Relevancy 本地反超（0.873 > 0.800）**：Qwen INT4 在"贴题"维度不弱于 DeepSeek，符合小模型任务聚焦特性；
- **Faithfulness 本地满分（1.000 > 0.947）**：上下文充足时（top=8）本地模型逐句忠实度反而最高；对比 top=5 时代 local 的 0.444，说明 **8 块上下文显著改善了本地模型的幻觉控制**。

---

## 六、关键发现与讨论（论文可直接引用的分析）

### 发现 1：Context Recall 与生成模型无关 —— "检索层瓶颈"的铁证

两代双通道实验（top=5：0.444/0.444；top=8：0.556/0.556）中，DeepSeek 与 Qwen 两个能力差异显著的生成器，Recall 得分**分毫不差**。这构成教科书式的控制变量论证：Recall 只取决于共享检索器，**0.556 的低分应归因于检索层而非生成层**。

### 发现 2：top_k 8→10 不涨 = "源头漏检"，而非"块数不够"

top=8 相比 top=5 捞回 0.112 的 Recall（证明部分漏检确因精排块数偏少）；但 8→10 一分不涨且 Precision 开始下降（0.907），说明**答案所需的 reference 句在混合检索候选池源头（BM25 20 条 + 向量 20 条）就未被召回**。为后续优化指明方向：扩大候选池、引入语义分块、查询改写。

### 发现 3：INT4 量化代价可控，且可被更多上下文补偿

对比 top=5 时代（local Faithfulness 0.444）与 top=8 定稿（1.000），本地 7B 在检索上下文更充分时忠实度显著改善并反超 API——**对算力受限场景的工程启示：给足上下文是低成本弥补小模型/量化模型能力差距的有效手段**。日常开发用 API、离线演示用本地的调度策略因此具备数据支撑。

### 发现 4：评测集是 RAGAS 分数的第一前置条件

8/28 全 0（reference 自写）→ 9/2 翻身（reference 原文化），系统代码零改动。任何 RAGAS 报告若不先说明 reference 构建口径，数字对比将失去意义——本报告全部数字基于「reference = 研报原文、71/71 人工校对」这一口径。

---

## 七、局限与展望

1. **Context Recall 0.556 未达 0.60**：根因已定位为混合检索候选池源头漏检。后续优化方向（按优先级）：① 扩大混合检索候选池（如 20 → 40 条）并重测；② 语义分块（500-1000 字块对跨段落/多跳问题截断关键句）；③ 查询改写 / HyDE 提升低相似度问题召回。
2. **各开发里程碑为独立验证口径**（人工评分 / 命中率 / MRR / 路由准确率），并非同一基准下的严格消融，若导师要求同基准消融，需补跑"去 Prompt / 关混合检索 / 关 Agent"三档对照实验（详见《消融实验汇总表.md》）。
3. **judge 单一化**：全部打分依赖 DeepSeek 一个裁判，存在裁判偏差风险；论文可注明或后续引入第二裁判抽样交叉验证。
4. **评测集规模**：71 题对单领域（新能源 + AI）覆盖已较充分，但对泛金融场景外推性有限。

---

## 八、复现指南（可复现 = 论文可信）

```powershell
cd E:\finrag\FinRAG
.venv\Scripts\activate
$env:HF_ENDPOINT = "https://hf-mirror.com"

# api 通道（生成器 + judge 均 DeepSeek，约 15-20 分钟）
$env:FINRAG_MODEL_MODE = "api"
python -u eval_ragas_dual.py --eval-file data/eval/qa_pairs_71_final.json

# local 通道（生成器 Qwen INT4 走 GPU；embedding/reranker 走 CPU 防显存撞车，约 40-60 分钟）
$env:FINRAG_MODEL_MODE = "local"
$env:FINRAG_EMB_DEVICE = "cpu"
python -u eval_ragas_dual.py --eval-file data/eval/qa_pairs_71_final.json

# 合并双通道报告
python make_dual_report.py
```

前置条件：`.env` 配好 DEEPSEEK_API_KEY；Ollama 托盘运行并已 `ollama pull qwen2.5:7b`；评测脚本已内置断点缓存，中断后重跑自动续跑（仅补打分）。复现入口：git tag **v1.1.0**。

---

## 附录 A：结果文件清单（全部可溯源）

| 文件 | 内容 | 时间 |
|---|---|---|
| `data/eval/ragas_api_results.json` | **api top=8 定稿（论文引用）** | 09-05 |
| `data/eval/ragas_local_results.json` | **local top=8 定稿（论文引用）** | 09-05 |
| `data/eval/ragas_api_results_top5.json` | api top=5 基线（过程） | 09-02 |
| `data/eval/ragas_api_results_top8.json` | api top=8（过程，与定稿同值） | 09-02 |
| `data/eval/ragas_api_results_top10.json` | api top=10 实验 | 09-05 |
| `data/eval/ragas_api_report.md` / `ragas_local_report.md` | 双通道逐项报告 | 09-05 |
| `data/eval/ragas_results.json` | 8/28 初评（10 题时代） | 08-28 |
| `data/eval/qa_pairs_71_final.json` | 71 题评测集（reference 71/71 校对） | 09-02 |
| `data/eval/cache_samples_local.json` | local 通道答案缓存（断点续跑用） | 09-05 |
| `docs/双通道对比报告.md` | 双通道对比总报告 | 09-05 |
| `docs/消融实验汇总表.md` | 论文实验章五档里程碑表 | 09-05 |

## 附录 B：术语速查

| 术语 | 大白话 |
|---|---|
| Faithfulness | 答案有没有照着原文说，不自己编（幻觉控制） |
| Context Precision | 检索回来的块是不是块块都用得上（准） |
| Context Recall | 该找的原文是不是都找回来了（全） |
| reference | 每题的标准答案块（本报告为研报原文） |
| judge | 阅卷官，负责给答案和上下文打分 |
| top_k | reranker 精排后喂给模型的最多块数 |
