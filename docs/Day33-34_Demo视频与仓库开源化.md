# Day 33-34 小白操作指南：录制 Demo 视频 + GitHub 仓库开源化

> 日期：2026-08-29 ｜ 项目：FinRAG v3.0 ｜ 导师方案：Day 35 + 第 6 周 Day 5
> 你的 API 已切换 **DeepSeek**，界面/后端/Release 已全部完成（v1.0.0）。

---

## 一、先看导师要求（PDF 原文摘录）

### Day 35：录制 Demo
- 录制 **3-5 分钟**的演示视频
- 展示：上传研报 → 问答 → 引用标注 → 数值推理 → Agent 查实时数据 → 双模式切换
- 展示 RAGAS 评估报告
- 产出：Demo 演示视频
- 检查：**视频清晰、流程完整、有讲解**

### 第 6 周 Day 5：GitHub 仓库优化（提前做）
- 完善 README（项目简介、架构图、安装步骤、使用示例、评估结果）
- 添加 License（MIT）
- 代码注释和类型标注检查
- 添加 Contributing.md 和 CHANGELOG.md
- 检查：**陌生人能按 README 跑通项目**

### 你的现状（我查过了）
| 项目 | 状态 |
|---|---|
| Gradio 界面 + FastAPI + v1.0.0 | ✅ 已完成 |
| 演示素材 | docs/screenshots/ 有 Swagger 截图，docs/ 有 week5_1.png、week5_2.png |
| README | ✅ 已更新到 Day 29 + 主视觉图 |
| License / CHANGELOG / Contributing | ❌ 还没有 |
| 录制工具 | 电脑自带（Xbox Game Bar / Win+G） |

---

## 二、核心概念解释（零基础版）

### 1. Demo 视频是什么？
大白话：**把你 6 周做的东西"演"给面试官看**，3-5 分钟。面试官没时间看代码，看视频最快。
类比：买车看广告片 vs 看发动机图纸——视频是广告片，代码是图纸。

### 2. 为什么需要讲解词（脚本）？
大白话：**不写稿会卡壳**。录之前把每一句要说什么写下来，照着念，视频才流畅。
面试官要看到的是"你懂你的系统"，不是"你会点按钮"。

### 3. License / CHANGELOG / Contributing 是什么？
| 文件 | 大白话 | 作用 |
|---|---|---|
| LICENSE | 版权声明（MIT = 允许别人自由使用） | 开源项目的"身份证" |
| CHANGELOG.md | 版本更新日志（v0.1 → v1.0 干了啥） | 让别人看到你的演进过程 |
| CONTRIBUTING.md | "欢迎来贡献"的说明 | 加分项，体现开源素养 |

---

## 三、Day 33 详细步骤：录制 Demo 视频

### 步骤 1：准备录制环境

**Windows 自带录屏**（最简单，不用装软件）：
1. 按 `Win + G`（会弹出 Xbox Game Bar 工具条）
2. 点红色的"录制"圆钮（或 `Win + Alt + R` 直接开录）
3. 结束录制：点工具条上的方块停止，视频自动存到 `C:\Users\PC\Videos\Captures\`

> 或者用 OBS Studio（免费，能录桌面+麦克风，需要下载安装）。小白建议先用 Win+G 自带。

### 步骤 2：准备讲解词（照这个念）

**总时长 3-5 分钟，分 6 段**：

```
【开场】0:00-0:20
"大家好，这是我的 FinRAG 金融研报智能问答系统。它基于 RAG + Agent 双架构，
能回答研报内容问题、查询实时行情，还能做研报预测和实际数据的对比分析。"

【演示1 研报问答】0:20-1:10
启动：python app_gradio.py → 浏览器打开 127.0.0.1:7860
"首先看研报问答能力。我输入'宁德时代的主营业务是什么'——
系统从 21 份研报、1323 个知识块中检索相关内容，给出带引用来源的回答。
大家看下面的引用区，它明确标注了引用了哪份研报、哪个段落。"

【演示2 实时行情】1:10-2:00
切换到 agent 模式 → 输入"宁德时代今天股价多少"
"第二个能力是 Agent 工具调用。我切换到 agent 模式，问'宁德时代今天股价多少'，
LLM 自主决定调用 get_stock_price 工具。注意看，它没有编造数据，
而是通过工具查询后给出回答——这就是大模型和外部数据源的连接。"

【演示3 综合对比】2:00-2:50
输入"研报说宁德时代营收增长20%，实际是多少"
"第三个能力是 RAG + Agent 协同。这个问题同时涉及研报预测和实际数据——
系统先检索研报找到预测值，再调用工具拿到实际值，最后对比分析给出结论。
这体现了我说的'开卷考试 + 允许用计算器'的设计理念。"

【演示4 评估报告】2:50-3:40
打开 docs/RAGAS评估报告.md
"最后看量化评估。我用 RAGAS 框架做了 4 项指标评估，
Answer Relevancy 达到 0.798。此外检索 Hit Rate 100%、路由准确率 100%、
Prompt 优化提升 48.6%——我的系统有数据支撑，不是'感觉还不错'。"

【结尾】3:40-4:00
"以上就是 FinRAG 的核心能力，感谢观看。"
```

### 步骤 3：录屏（按脚本走）

1. 提前**跑好** Gradio 服务（`python app_gradio.py`，等模型加载完）
2. 按 `Win + G` 打开录屏，开始录制
3. 按脚本一步步操作：**打开浏览器 → 输入问题 → 等回答 → 指给镜头看引用区**
4. 每步操作**慢一点**，让观众看清界面变化
5. 录制完停止，检查视频文件

### 步骤 4：检查视频（导师检查点）

| 检查项 | 要求 |
|---|---|
| 时长 | 3-5 分钟 |
| 清晰度 | 界面文字可读 |
| 流程完整 | 覆盖研报问答/实时行情/综合对比/评估报告 |
| 有讲解 | 全程有声音讲解（别只录画面） |

✅ 视频录完 = Day 33 完成。把视频文件路径发我。

---

## 四、Day 34 详细步骤：GitHub 仓库开源化

### 步骤 1：添加 LICENSE（MIT）

```powershell
New-Item -Path "E:\finrag\FinRAG\LICENSE" -ItemType File -Force
```

粘贴（把"2026 你的名字"改成你的真实姓名）：

```
MIT License

Copyright (c) 2026 你的名字

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 步骤 2：添加 CHANGELOG.md（版本日志）

```powershell
New-Item -Path "E:\finrag\FinRAG\CHANGELOG.md" -ItemType File -Force
```

粘贴：

```markdown
# CHANGELOG

## [v1.0.0] - 2026-08-29

### 新增
- RAG + Agent 协同系统（路由分诊：研报问题→RAG / 实时问题→Agent / 混合→协同）
- Agent 工具调用（get_stock_price / get_financial_data，三级降级）
- FastAPI 后端（/health /query /agent_query + Swagger 文档）
- Gradio 完整 Web 界面（对话 + 引用展示 + 工具调用可视化）
- Dockerfile + docker-compose.yml（容器化部署配置）
- RAGAS 量化评估（4 项指标，Answer Relevancy 0.798）

### 优化
- Prompt A/B 测试：P3 模板胜出，回答质量 +48.6%
- 混合检索 + Reranker 重排：Hit Rate 100%，MRR 1.000

## [v0.6.0] - 2026-08-28

### 新增
- FastAPI 后端 + Docker 配置

## [v0.5.0] - 2026-08-28

### 新增
- RAGAS 量化评估

## [v0.4.0] - 2026-08-19

### 新增
- RAG + Agent 协同（路由 + 综合推理）

## [v0.3.0] - 2026-08-17

### 新增
- Agent 工具调用（股价/财务查询）
```

### 步骤 3：添加 CONTRIBUTING.md

```powershell
New-Item -Path "E:\finrag\FinRAG\CONTRIBUTING.md" -ItemType File -Force
```

粘贴：

```markdown
# 贡献指南

欢迎为 FinRAG 贡献代码！请遵循以下流程：

1. **Fork 本仓库** 并克隆到本地
2. 创建功能分支：`git checkout -b feature/你的功能`
3. 提交改动：`git commit -m "feat: 描述你的改动"`
4. 推送分支：`git push origin feature/你的功能`
5. 创建 **Pull Request**，说明改动内容

## 代码规范
- Python 3.11，遵循 PEP 8
- 新增功能需附带测试脚本
- 提交信息格式：`feat:` / `fix:` / `docs:` / `refactor:`

## 问题反馈
遇到 Bug 或使用问题，请在 Issues 中提出，附上复现步骤和错误信息。
```

### 步骤 4：完善 README 的"快速开始"（确保陌生人能跑通）

你的 README 已经有完整内容。**补一处**：在 README 顶部主视觉图下方加一行使用说明（可选）：

```markdown
> 🚀 快速体验：`pip install -r requirements.txt` → 配置 `.env` → `python app_gradio.py`
```

### 步骤 5：提交 + 推送

```powershell
git add LICENSE CHANGELOG.md CONTRIBUTING.md README.md
git commit -m "docs: 仓库开源化（License MIT + CHANGELOG + Contributing + README 完善）"
git push origin main
```

> ⚠️ push 超时就连手机热点，或分多次重试。

### 步骤 6：最终 Release 检查

浏览器打开 `https://github.com/sharkmate0127/FinRAG/releases`，确认：
- v1.0.0 Release 已发布（昨天做过就跳过）
- Release 描述包含：核心能力、量化结果、使用方式
- 有 README 预览（首页自动显示）

---

## 五、面试话术

**Q: 你的项目怎么让面试官快速了解？**

> "我录了 4 分钟的 Demo 视频，完整演示：研报问答（带引用溯源）→ Agent 查实时行情 → RAG+Agent 协同对比 → RAGAS 评估报告。面试官看视频就能理解系统全貌。"

**Q: 你的项目开源素养？**

> "GitHub 仓库有完整的 README（架构图+安装+评估结果）、MIT License、CHANGELOG 版本日志、CONTRIBUTING 贡献指南，v1.0.0 Release 带发布说明。陌生人按 README 能跑通项目。"

**Q: 项目最大的难点？**

> "RAG + Agent 协同的路由设计是最大挑战——要判断问题属于研报类、实时类还是混合类。我用 LLM 路由 + 10 题测试集验证，准确率 100%。另外解决了 ragas 和 DeepSeek 的兼容性问题（strictness 从 3 改到 1）。"

---

## 六、常见问题排错

| 现象 | 原因 | 解决 |
|---|---|---|
| 录屏没有声音 | Xbox Game Bar 没开麦克风 | Win+G → 麦克风图标打开 |
| 视频找不到 | 录制没成功 | 检查 `C:\Users\PC\Videos\Captures\` |
| 视频太长 | 操作慢+等待多 | 剪掉等待时间（用 Clipchamp 免费剪辑） |
| push 超时 | GitHub 443 阻塞 | 连手机热点 / 分多次重试 |
| Release 没显示 | 没发布 | 到 Releases → Create new release |

---

## 七、验收清单（对照导师检查点）

- [ ] Day 33：Demo 视频录制完成（3-5 分钟，有讲解）
- [ ] Day 33：视频覆盖 4 大能力（研报问答/实时行情/综合对比/评估报告）
- [ ] Day 34：LICENSE（MIT）已添加
- [ ] Day 34：CHANGELOG.md + CONTRIBUTING.md 已添加
- [ ] Day 34：README 陌生人可跑通
- [ ] Day 34：commit + push + v1.0.0 Release 确认

---

## 八、第 6 周预告（论文 + 面试）

- Day 1-2：论文第一章（引言：选题背景、问题定义、研究意义）1500-2000 字
- Day 3：论文第二章（相关工作：RAG 演进、金融 NLP）2000-2500 字
- Day 4：论文第三章（系统设计：架构图、RAG 算法、Prompt 策略）2000-2500 字
- Day 5：GitHub 仓库最终优化（License 等，已提前做）
- Day 6：面试准备（简历更新、5 分钟电梯演讲、STAR 话术）
- Day 7：收尾复盘 + 论文初稿提交
