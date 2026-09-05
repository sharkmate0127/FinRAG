# FinRAG 方案 A 双模型迁移小白操作指南

> 目标：云端使用 DeepSeek API，本地使用 Qwen2.5-7B-Instruct + Ollama + INT4。
> 重要边界：本指南只提供操作方法；你需要自己复制、粘贴、保存和运行，我不替你修改项目文件。
> 适用项目：`E:\finrag\FinRAG`

---

## 一、先理解方案 A：不是“二选一”，而是“双通道”

导师方案的核心结论是：

| 通道 | 模型 | 运行方式 | 主要用途 |
|---|---|---|---|
| 云端通道 | DeepSeek `deepseek-chat` | API 调用 | 日常开发、RAG 高质量回答、Agent/Function Calling |
| 本地通道 | Qwen2.5-7B-Instruct | Ollama 本地运行，模型采用量化版本 | 离线演示、无 API 费用、双部署对照评估 |

这不是让两个模型“抢着回答同一个问题”，而是让系统可以切换：

```text
mode=api    → DeepSeek API
mode=local  → 本机 Ollama → Qwen2.5-7B-Instruct
```

### 为什么本地不换 DeepSeek？

1. DeepSeek API 背后的模型规模和本地可运行的蒸馏模型不是同一个量级。
2. DeepSeek 推理模型本地运行可能响应慢、输出冗长，不适合现场 Demo。
3. 你的 RTX 4060 只有 8GB 显存，Qwen2.5-7B 的 INT4 量化更适合本地运行。
4. 同一个 Qwen 模型做“云端/本地”对照，变量更少，实验更严谨。

> 面试背诵：我的系统采用双模型双部署架构：云端用 DeepSeek API 保证推理质量与调用成本，本地用 Qwen2.5-7B INT4 量化保证离线可用性。两条通道共享同一套 RAG 检索、Prompt 和评测集，因此可以比较部署方式对回答质量的影响。

---

## 二、先不要改代码：备份和检查

### 第 1 步：打开 PowerShell

按 `Win` 键，输入 `PowerShell`，回车。

### 第 2 步：进入项目目录

```powershell
cd E:\finrag\FinRAG
```

确认位置：

```powershell
Get-Location
```

期望看到：

```text
Path
----
E:\finrag\FinRAG
```

### 第 3 步：备份当前项目

> 这一步只复制，不删除、不修改原项目。

```powershell
Copy-Item "E:\finrag\FinRAG" "E:\FinRAG_before_dual_model" -Recurse
```

检查备份：

```powershell
Test-Path "E:\FinRAG_before_dual_model"
```

期望结果：

```text
True
```

### 第 4 步：确认当前 DeepSeek 配置

打开项目里的 `.env` 文件，应该类似这样：

```text
DEEPSEEK_API_KEY=sk-你的真实Key
```

注意：

- 不要把真实 Key 发到聊天、截图或 GitHub。
- `.env` 必须在项目根目录：`E:\finrag\FinRAG\.env`。
- 文件名不能是 `.env.txt`。
- 如果使用记事本保存，选择“所有文件”，文件名输入 `.env`，编码选 UTF-8。

检查 `.gitignore` 里有：

```text
.env
.venv/
```

### 第 5 步：先测试 DeepSeek 云端通道

当前 PowerShell 如果没有激活虚拟环境，执行：

```powershell
.\.venv\Scripts\Activate.ps1
```

设置 HuggingFace 镜像：

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

运行：

```powershell
python call_qwen.py
```

虽然文件名还叫 `call_qwen.py`，但你之前已经把它改成 DeepSeek 配置了。只要能输出模型回答，就说明云端通道正常。

> 建议后续把文件重命名为 `call_deepseek.py`，但这是可选整理，不要在验证前做大范围改名。

---

## 三、安装本地 Ollama

### 1. Ollama 是什么？

Ollama 是本地大模型运行器，作用类似“本地模型播放器”：

- Qwen 模型文件是“电影文件”。
- Ollama 是“播放器”。
- Python 程序通过 `http://127.0.0.1:11434` 调用播放器。

Ollama 本身不是大模型，Qwen2.5-7B 才是模型。

### 2. 安装方式

浏览器打开 Ollama 官方网站，下载 Windows 安装包并安装。

如果你已经下载好安装包：

1. 双击安装包。
2. 按默认选项安装。
3. 安装完成后重新打开 PowerShell。
4. 不要急着运行项目，先验证命令。

验证：

```powershell
ollama --version
```

能看到版本号就说明安装成功。

如果提示：

```text
ollama 不是内部或外部命令
```

处理方法：

1. 关闭当前 PowerShell。
2. 重新打开 PowerShell。
3. 再运行 `ollama --version`。
4. 如果仍然找不到，再把完整错误截图发我，不要自行修改 PATH。

### 3. 下载 Qwen2.5-7B

```powershell
ollama pull qwen2.5:7b
```

说明：

- 这个模型文件可能需要数 GB 空间。
- 下载时间受网络影响，可能较久。
- 不要关闭正在下载的窗口。
- 如果下载中断，重新执行同一条命令即可，通常会继续或重新校验。

查看模型是否存在：

```powershell
ollama list
```

期望看到类似：

```text
NAME           ID              SIZE
qwen2.5:7b     ...             ...GB
```

### 4. 直接测试 Qwen

```powershell
ollama run qwen2.5:7b
```

进入后输入：

```text
用一句话解释什么是 RAG
```

能得到回答后，输入：

```text
/bye
```

退出。

> 这一步验证的是 Ollama + Qwen 本地模型本身，还没有接入你的 FinRAG 项目。

---

## 四、理解两套接口为什么可以共用一套代码

### DeepSeek 云端调用

你的项目当前配置大致是：

```python
llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    temperature=0.2,
)
```

### Ollama 本地调用

Ollama 提供 OpenAI 兼容接口，可以使用同一个 `ChatOpenAI` 类：

```python
local_llm = ChatOpenAI(
    api_key="ollama",
    model="qwen2.5:7b",
    base_url="http://127.0.0.1:11434/v1",
    temperature=0.2,
)
```

关键变化只有三项：

| 配置 | DeepSeek | Ollama + Qwen |
|---|---|---|
| API Key | `.env` 中的真实 Key | 任意占位字符串，如 `ollama` |
| model | `deepseek-chat` | `qwen2.5:7b` |
| base_url | `https://api.deepseek.com` | `http://127.0.0.1:11434/v1` |

这就是“OpenAI 兼容协议”的价值：上层代码基本不用重写，只换配置。

---

## 五、创建一个双模式最小测试文件

> 这一文件先单独测试模型切换，不要一开始就改 `ask.py`、`rag_agent.py` 和 `app_gradio.py`。

### 第 1 步：创建文件

在项目目录执行：

```powershell
New-Item -Path "E:\finrag\FinRAG\dual_model_test.py" -ItemType File -Force
```

也可以手动创建：

`E:\finrag\FinRAG` 文件夹右键 → 新建 → 文本文档 → 重命名为 `dual_model_test.py`。

> 如果系统隐藏扩展名，请先在文件夹“查看”中勾选“文件扩展名”，避免生成 `dual_model_test.py.txt`。

### 第 2 步：粘贴完整代码

```python
# -*- coding: utf-8 -*-
"""dual_model_test.py - DeepSeek API / Qwen Ollama 双模式最小测试"""
import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

MODE = os.getenv("FINRAG_MODEL_MODE", "api").lower()


def build_llm(mode: str):
    """根据 mode 创建云端或本地 LLM"""
    if mode == "local":
        print("当前模式：local（Ollama + Qwen2.5-7B）")
        return ChatOpenAI(
            api_key="ollama",
            model="qwen2.5:7b",
            base_url="http://127.0.0.1:11434/v1",
            temperature=0.2,
        )

    if mode == "api":
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise RuntimeError("没有找到 DEEPSEEK_API_KEY，请检查 .env")
        print("当前模式：api（DeepSeek）")
        return ChatOpenAI(
            api_key=api_key,
            model="deepseek-chat",
            base_url="https://api.deepseek.com",
            temperature=0.2,
        )

    raise ValueError("FINRAG_MODEL_MODE 只能是 api 或 local")


if __name__ == "__main__":
    try:
        llm = build_llm(MODE)
        response = llm.invoke("用一句话解释什么是 RAG，并说明它为什么能减少大模型幻觉。")
        print("模型回答：")
        print(response.content)
    except Exception as e:
        print(f"调用失败：{type(e).__name__}: {e}")
        sys.exit(1)
```

### 第 3 步：测试云端 DeepSeek

```powershell
$env:FINRAG_MODEL_MODE = "api"
python dual_model_test.py
```

期望看到：

```text
当前模式：api（DeepSeek）
模型回答：
...
```

### 第 4 步：测试本地 Qwen

先确保 Ollama 在运行，并且模型已经下载：

```powershell
ollama list
```

然后执行：

```powershell
$env:FINRAG_MODEL_MODE = "local"
python dual_model_test.py
```

期望看到：

```text
当前模式：local（Ollama + Qwen2.5-7B）
模型回答：
...
```

### 第 5 步：清除当前终端的模式变量

```powershell
Remove-Item Env:FINRAG_MODEL_MODE -ErrorAction SilentlyContinue
```

不清除也没关系，但要记住：当前终端设置的环境变量会影响后续运行。

---

## 六、把双模式接入 FinRAG：推荐最小改法

不要把 DeepSeek 和 Qwen 的配置散落到 10 个文件里。正确做法是集中到一个配置模块。

### 第 1 步：创建 `model_config.py`

```powershell
New-Item -Path "E:\finrag\FinRAG\model_config.py" -ItemType File -Force
```

粘贴：

```python
# -*- coding: utf-8 -*-
"""model_config.py - FinRAG 双模型配置中心"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_model_mode() -> str:
    """读取模型模式；默认使用 DeepSeek API"""
    mode = os.getenv("FINRAG_MODEL_MODE", "api").lower().strip()
    if mode not in {"api", "local"}:
        raise ValueError("FINRAG_MODEL_MODE 必须是 api 或 local")
    return mode


def build_llm():
    """统一构造 DeepSeek 或 Qwen Ollama LLM"""
    mode = get_model_mode()

    if mode == "local":
        return ChatOpenAI(
            api_key="ollama",
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
            temperature=0.2,
        )

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("FINRAG_MODEL_MODE=api，但没有找到 DEEPSEEK_API_KEY")

    return ChatOpenAI(
        api_key=api_key,
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        temperature=0.2,
    )


def describe_mode() -> str:
    """返回当前模式的可读说明"""
    if get_model_mode() == "local":
        return "local / Ollama / Qwen2.5-7B"
    return "api / DeepSeek / deepseek-chat"
```

### 第 2 步：先测试配置中心

在 `dual_model_test.py` 中，不要马上删除原代码。你可以另建一个小测试文件，或者暂时把调用部分改成：

```python
from model_config import build_llm, describe_mode

print("当前模型：", describe_mode())
llm = build_llm()
response = llm.invoke("用一句话解释 RAG")
print(response.content)
```

分别测试：

```powershell
$env:FINRAG_MODEL_MODE = "api"
python dual_model_test.py

$env:FINRAG_MODEL_MODE = "local"
python dual_model_test.py
```

两种模式都成功后，才继续替换主项目中的模型初始化。

### 第 3 步：替换 `ask.py` 的模型初始化

打开：

```powershell
notepad "E:\finrag\FinRAG\ask.py"
```

找到类似这一段：

```python
llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    temperature=0.2,
)
```

替换为：

```python
from model_config import build_llm, describe_mode

print("当前模型：", describe_mode())
llm = build_llm()
```

注意：

- 只替换“创建 llm 的部分”。
- 不要删除 RAG 检索、Prompt、引用溯源、history 等代码。
- 先复制备份再保存。

### 第 4 步：替换 `rag_agent.py` 的模型初始化

打开：

```powershell
notepad "E:\finrag\FinRAG\rag_agent.py"
```

找到它当前创建 `ChatOpenAI` 的部分，替换为：

```python
from model_config import build_llm, describe_mode

print("当前模型：", describe_mode())
llm = build_llm()
```

注意：Agent 的工具调用最好优先用 DeepSeek API 验证。原因是：

- 云端 DeepSeek Function Calling 已经跑通。
- 本地 Qwen 是否能稳定输出工具调用，取决于 Ollama 版本、模型模板和本地模型能力。
- 方案 A 的本地通道主要用于离线 RAG 演示和双模式对比，不要求本地 Qwen 一定承担全部 Agent 工具能力。

### 第 5 步：更新 `.env` 的可选配置

在 `.env` 里可以增加：

```text
DEEPSEEK_API_KEY=sk-你的Key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
```

不要把这一行写成：

```text
FINRAG_MODEL_MODE=local
```

除非你希望每次默认使用本地 Qwen。更推荐把模式留在 PowerShell 临时切换：

```powershell
$env:FINRAG_MODEL_MODE = "api"
python ask.py

$env:FINRAG_MODEL_MODE = "local"
python ask.py
```

这样不容易忘记当前到底使用了哪个模型。

---

## 七、双模式运行顺序

### 方案 A：云端 DeepSeek（日常开发推荐）

```powershell
cd E:\finrag\FinRAG
.\.venv\Scripts\Activate.ps1
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:FINRAG_MODEL_MODE = "api"
python ask.py
```

用于：

- RAG 质量开发
- Agent 工具调用
- 评测脚本
- Prompt 调试
- Gradio 日常演示

### 方案 B：本地 Qwen（离线演示）

先确认 Ollama：

```powershell
ollama list
```

再运行：

```powershell
cd E:\finrag\FinRAG
.\.venv\Scripts\Activate.ps1
$env:FINRAG_MODEL_MODE = "local"
python ask.py
```

用于：

- 没有网络时的离线 RAG 演示
- 不消耗 DeepSeek API 额度
- API 与本地部署对照评估

### 查看当前模式

每次启动时应该看到：

```text
当前模型： api / DeepSeek / deepseek-chat
```

或者：

```text
当前模型： local / Ollama / Qwen2.5-7B
```

如果看不到这行，说明模型配置中心可能没有被主程序调用。

---

## 八、双模式对比实验怎么做

### 1. 为什么要“同一批问题”

如果 API 模式测 10 道题，本地模式测另一批题，结果无法公平比较。正确做法是：

```text
同一评测集
同一 Prompt
同一检索结果
只改变模型部署方式
```

这叫控制变量实验。

### 2. 对比记录表

在 Word、Excel 或 Markdown 中建立：

| 问题编号 | 问题 | API 答案 | 本地答案 | API 用时 | 本地用时 | API 分数 | 本地分数 |
|---|---|---|---|---:|---:|---:|---:|
| 1 | 宁德时代营收预测 |  |  |  |  |  |  |
| 2 | 比亚迪净利润预测 |  |  |  |  |  |  |
| 3 | 两家公司营收对比 |  |  |  |  |  |  |

### 3. 至少覆盖四类问题

1. 事实类：某公司的主营业务是什么？
2. 数值类：某年营收/净利润是多少？
3. 推理类：两年增长率是多少？
4. 对比类：宁德时代和比亚迪的营收规模有什么差异？

### 4. 记录指标

重点记录：

- 回答是否引用了正确研报。
- 数值是否正确。
- 计算过程是否完整。
- 是否出现幻觉。
- 是否答非所问。
- 首字延迟和总响应时间。

### 5. 面试中如何说

不要说“Qwen 不如 DeepSeek”。更准确的说法是：

> 在相同 RAG 检索结果和 Prompt 下，我比较了 DeepSeek API 与本地 Qwen2.5-7B INT4 的表现。API 通道在复杂数值推理上更稳定，本地通道的优势是免费、离线和数据不出本机。最终根据场景选择模型，而不是简单判断某个模型绝对更好。

如果你还没有实际跑出本地评估数字，就不要直接背“85% vs 78%”。应说：

> 这组数字需要在同一评测集上正式重跑后确认，目前先完成双模式接入和测试框架。

---

## 九、模型选择、RAG 和 Agent 的关系

### 模型层

DeepSeek 和 Qwen 都是“负责理解和生成文字”的大模型。

### RAG 层

RAG 负责“从研报知识库找资料”。模型换了，RAG 的检索流程不应该跟着重写。

```text
PDF → 分块 → Embedding → ChromaDB → 检索 → 上下文
```

### Agent 层

Agent 负责“判断是否调用工具”。

```text
用户问题 → 模型判断 → tool_call → Python 工具 → 工具结果 → 模型回答
```

### 服务层

FastAPI 和 Gradio 负责“让用户能使用系统”。

```text
FastAPI：给程序调用
Gradio：给人操作
```

因此，这次迁移主要修改的是**模型适配层**，不应破坏：

- ChromaDB 向量库
- bge-large-zh-v1.5 Embedding
- bge-reranker-large
- BM25 混合检索
- 引用溯源
- Few-Shot Prompt
- FastAPI 接口
- Gradio 界面

---

## 十、常见错误和处理顺序

### 错误 1：`ollama is not recognized`

含义：Ollama 没安装好或 PowerShell 没刷新 PATH。

处理：关闭 PowerShell，重新打开，再运行：

```powershell
ollama --version
```

### 错误 2：`connection refused 127.0.0.1:11434`

含义：Python 找得到本地地址，但 Ollama 服务没启动。

处理：

1. 从开始菜单打开 Ollama。
2. 等它在后台运行。
3. 再执行：

```powershell
ollama list
```

### 错误 3：`model qwen2.5:7b not found`

处理：

```powershell
ollama pull qwen2.5:7b
```

### 错误 4：DeepSeek 模式提示没有 Key

检查：

```powershell
Get-Content "E:\finrag\FinRAG\.env"
```

不要把输出截图发出来，因为可能包含 Key。只确认是否存在 `DEEPSEEK_API_KEY=`。

### 错误 5：本地回答很慢

正常原因：本地模型依赖 CPU/GPU 和显存，速度通常比云端慢。

处理：

- 先等待完整回答。
- 减少 Prompt 长度。
- 只检索 Top-3 或 Top-5 做演示。
- 不要同时打开多个本地模型进程。

### 错误 6：本地模型输出格式差

可能原因：

- Qwen 模型模板不匹配。
- Ollama 版本不同。
- 本地量化损耗。
- Agent 工具调用能力不稳定。

处理原则：先保证本地 RAG 能回答，再考虑本地 Agent。方案 A 不要求本地 Qwen 一开始就完全复制 DeepSeek 的工具调用表现。

### 错误 7：切换后不知道当前模型

必须在启动时打印：

```text
当前模型： api / DeepSeek / deepseek-chat
```

或：

```text
当前模型： local / Ollama / Qwen2.5-7B
```

---

## 十一、提交前检查清单

### 云端 DeepSeek

- [ ] `.env` 中有 `DEEPSEEK_API_KEY`
- [ ] `python dual_model_test.py` 的 api 模式成功
- [ ] `python agent_demo.py` 能完成工具调用
- [ ] `python ask.py` 能完成 RAG 问答
- [ ] `python app.py` 的 `/health` 正常
- [ ] Gradio 界面能正常回答

### 本地 Qwen

- [ ] `ollama --version` 有版本号
- [ ] `ollama list` 能看到 `qwen2.5:7b`
- [ ] `ollama run qwen2.5:7b` 能回答问题
- [ ] `dual_model_test.py` 的 local 模式成功
- [ ] `ask.py` 的 local 模式能完成至少一个研报问题
- [ ] 已记录 API/本地的回答质量和响应时间

### 项目安全

- [ ] `.env` 没有加入 Git
- [ ] 没有把 API Key 写死在 Python 文件里
- [ ] 没有删除原来的 `data/vector_db`
- [ ] 没有删除 `data/chunks/chunks.jsonl`
- [ ] 修改前有 `E:\FinRAG_before_dual_model` 备份

---

## 十二、推荐提交方式

完成最小测试后再提交，不要一开始就提交半成品：

```powershell
git status
git add model_config.py dual_model_test.py ask.py rag_agent.py
git commit -m "feat: add DeepSeek API and local Qwen dual-model configuration"
```

如果你还没有正式完成本地 Qwen 接入，就不要提前打 v1.1.0。可以先用：

```text
双模型接入开发中
```

等两种模式都能实际跑通并完成对比评估后，再发布版本。

---

## 十三、最终面试背诵版

### 30 秒版

> 我的 FinRAG 采用 DeepSeek API + 本地 Qwen2.5-7B INT4 的双模型双部署架构。云端 DeepSeek 负责开发期的高质量 RAG 推理和 Agent 工具调用，本地 Qwen 通过 Ollama 负责离线演示。两条通道共享同一套研报知识库、Embedding、混合检索、Prompt 和评测集，因此可以控制变量比较部署方式的影响。

### 为什么云端用 DeepSeek

> DeepSeek 兼容 OpenAI API 协议，接入 LangChain 时主要只需替换 base_url、API Key 和模型名；中文能力、成本和 Function Calling 都适合当前项目，迁移成本低。

### 为什么本地用 Qwen

> 本地层不是追求品牌一致，而是追求部署可行和实验严谨。我的 RTX 4060 只有 8GB 显存，Qwen2.5-7B 的 INT4 量化更适合本地运行，响应行为也更适合 RAG 问答演示。使用同一个 Qwen 模型做云端和本地的对照，比把 DeepSeek API 和 DeepSeek 蒸馏模型直接比较更严谨。

### 如果问“为什么不用本地 DeepSeek”

> 本地 DeepSeek 蒸馏模型会带来模型规模差异、响应速度和显存压力等问题，容易把部署方式对比变成模型大小对比。方案 A 保留本地 Qwen，可以更清楚地比较 API 和本地部署方式本身的影响。

### 如果问“模型换了，RAG 要重做吗”

> 不需要重做检索层。Embedding、ChromaDB、BM25 和 Reranker 属于知识检索模块，模型只是生成层。只要两个模型都遵循相同的 Prompt 和输入输出格式，就可以复用同一批检索结果和评测集。

### 如果问“两个模型谁更强”

> 我不简单做品牌排名，而是按场景选择。DeepSeek API 更适合高质量和 Agent 工具调用，本地 Qwen 更适合离线、低成本和隐私场景。最终用同一评测集上的 Faithfulness、Answer Relevancy、Context Precision、Context Recall、响应时间和工具调用成功率来决定。
