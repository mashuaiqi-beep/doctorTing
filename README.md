# doctorTing —— 医疗问诊分诊 Agent

> 一个从"能跑通的 Demo"逐步演进到"企业级 Agent 雏形"的实战项目。

doctorTing 做的事情很简单：**用户用自然语言描述自己的症状，系统通过多轮追问收集信息，识别风险，检索医学知识，最终给出分诊建议和科室推荐。**

但它不是医疗诊断系统，也不能开药方。它的核心价值在于展示：**如何把一个 LLM 应用，按企业级标准做工程化落地。**

---

## 一句话理解这个项目

```
你：我发烧两天了，还咳嗽
  → 系统：请问体温多少度？有没有呼吸困难？（追问缺失信息）
  → 你：38.5 度，没有呼吸困难
  → 系统：还需要了解...（继续追问或评估）
  → 系统：[分诊结果] 疑似上呼吸道感染，建议挂呼吸内科，以下是相关医学知识参考...
```

整个过程中，系统做了这些事：
- **抽取信息**：从口语中提取"发热""咳嗽"等结构化症状
- **风险识别**：用规则 + 大模型双层检查有没有"胸痛""呼吸困难"等红旗症状
- **状态维护**：用 Session 记住每一轮对话说了什么
- **知识检索**：从本地 50+ 疾病知识库中查找相关内容
- **生成建议**：结合问诊记录和知识库，给分诊建议

---

## 项目当前状态

三条核心接口已全部接入 LangGraph 流程编排：

| 接口 | 职责 | 编排方式 |
|------|------|----------|
| `POST /triage/start` | 首轮问诊 | LangGraph（6 个节点） |
| `POST /triage/continue` | 多轮追问 | LangGraph（7 个节点） |
| `POST /triage/evaluate` | 最终分诊 | LangGraph（9 个节点） |

此外还有：
- 前端问诊工作台（`/` 首页）
- Swagger 文档（`/docs`）
- 健康检查（`/health`）

---

## 架构总览

### 项目是怎么分层的

很多初学者会把逻辑全写在 API 函数里，但这个项目从第一天就按企业级习惯拆了层：

```
用户请求
  ↓
API 层（app/api/）        ← 只负责接收 HTTP 请求、校验参数、返回响应
  ↓
Service 层（app/service/） ← 编排业务流程，调用各种服务
  ↓
Agent 层（app/agent/）    ← LangGraph 定义流程节点和状态
  ↓
Core 层（app/core/）      ← 配置、Prompt 模板、风险规则
  ↓
Tools 层（app/tools/）    ← 可复用的工具函数
```

**为什么要这样拆？** 举个例子：将来你想把 Redis 换成数据库，只需要改 `session_store` 这一个地方，API 层完全不用动。这就是分层的意义。

### 核心概念解释

如果你刚开始接触 Agent 开发，这几个概念先搞懂：

| 概念 | 一句话解释 | 在这个项目里对应什么 |
|------|-----------|---------------------|
| **State（状态）** | 流程中各节点共享的数据包 | `StartTriageState` / `ContinueTriageState` / `EvaluateTriageState` |
| **Node（节点）** | 流程中的一个步骤 | `extract_info_node` → `check_rule_risk_node` → ... |
| **Graph（图）** | 把节点按顺序连起来的流程图 | `StateGraph`，定义了节点 A → 节点 B → ... 的执行顺序 |
| **Working Memory** | 系统记住的"已确认事实" | Session 里的 `confirmed_facts`，比如"已确认体温 38.5°C" |
| **RAG（检索增强生成）** | 先从知识库查资料，再让大模型回答 | evaluate 阶段先检索 `data/knowledge/` 再生成建议 |
| **Function Calling** | 大模型按指定格式输出，方便程序解析 | `ToolService.check_red_flags` 要求模型严格返回 risk_level |

### 一条请求的完整旅程（以 `/triage/start` 为例）

```
用户输入："我发烧两天了，还咳嗽"
  │
  ▼
节点 1 - extract_info       LLM 抽取 → symptoms: ["发热", "咳嗽"], missing_fields: ["体温", "呼吸困难"]
  │
  ▼
节点 2 - check_rule_risk    规则匹配 → 检查是否有"胸痛""咯血"等关键词
  │
  ▼
节点 3 - check_llm_risk     LLM Function Calling → 检查口语化表达（如"喘不上气"）
  │
  ▼
节点 4 - merge_risk         保守合并 → 任一方判高风险，最终就是高风险
  │
  ▼
节点 5 - save_session       写入 Redis → 保存症状、风险、缺失字段、追问问题
  │
  ▼
节点 6 - build_response     组装 JSON → 返回 session_id + 追问 + 风险等级
```

### 安全设计：双层风险识别

医疗场景最怕"漏判高风险"。这个项目用两层保险：

```
第一层：规则关键词（app/core/risk_rules.py）
  → 匹配"胸痛""意识模糊""咯血"等 14 个明确高危词
  → 优点：稳定、可解释、LLM 挂了也能跑

第二层：LLM 语义识别（app/service/tool_service.py）
  → 识别"胸口像被压着""人有点迷糊"等口语化表达
  → 优点：覆盖更广、理解上下文

合并策略：任一判 high → 最终 high，且后续追问不允许降级
```

---

## 目录结构

```
doctorTing/
├── app/
│   ├── main.py              FastAPI 应用入口
│   ├── api/                 路由层（triage_api.py）
│   ├── agent/               LangGraph 流程编排（triage_graph.py）
│   ├── schema/              Pydantic 请求/响应模型
│   ├── service/             业务服务层
│   │   ├── triage_service.py        核心编排（组装 Graph + 调用）
│   │   ├── llm_service.py           LLM 调用封装
│   │   ├── tool_service.py          工具调用（Function Calling）
│   │   ├── risk_control_service.py  规则风控
│   │   ├── session_store.py         内存会话存储
│   │   ├── redis_session_store.py   Redis 会话存储
│   │   ├── session_store_factory.py 存储工厂（自动选 Redis/内存）
│   │   ├── knowledge_service.py     知识检索
│   │   └── vector_knowledge_service.py ChromaDB 向量检索
│   ├── core/                配置 + Prompt + 规则
│   │   ├── config.py                环境变量配置
│   │   ├── prompt_manager.py        Prompt 模板集中管理
│   │   └── risk_rules.py            红旗症状关键词
│   ├── tools/               可复用工具函数
│   │   ├── extract_symptoms.py      症状抽取
│   │   ├── check_red_flags.py       红旗检查
│   │   ├── search_knowledge.py      知识检索
│   │   └── book_appointment.py      科室推荐/模拟挂号
│   ├── scripts/             脚本工具
│   │   └── build_knowledge_index.py 知识库索引构建
│   ├── static/              前端页面（HTML + CSS + JS）
│   └── utils/               通用工具（JSON 解析等）
├── data/
│   ├── knowledge/           医学知识库（50+ 疾病 Markdown 文档）
│   └── chroma/              ChromaDB 持久化目录
├── docs/                    设计文档
├── tests/                   自动化测试
├── .env.example             环境变量模板
└── README.md                你正在看的这个文件
```

---

## 快速启动

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo-url>
cd doctorTing

# 安装依赖
pip install -r docs/requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的配置：

```env
OPENAI_API_KEY=你的API_KEY
OPENAI_BASE_URL=https://api.deepseek.com    # 默认用 DeepSeek，可换成任一兼容接口
OPENAI_MODEL=deepseek-chat
REDIS_URL=redis://localhost:6379/0          # Redis 不可用时自动降级为内存存储
REDIS_SESSION_TTL_SECONDS=86400
CHROMA_PERSIST_DIR=data/chroma
```

> **提示**：项目默认使用 DeepSeek（便宜、中文好），但你用任何 OpenAI 兼容接口都行（通义千问、GLM 等）。

### 3. 构建知识库索引

```bash
python -m app.scripts.build_knowledge_index
```

这一步会读取 `data/knowledge/*.md`，切成段落，生成向量，存入 ChromaDB。只需执行一次，知识库更新后重新执行即可。

### 4. 启动服务

```bash
uvicorn app.main:app --reload
```

然后访问：
- **前端页面**：http://127.0.0.1:8000/
- **接口文档**：http://127.0.0.1:8000/docs
- **健康检查**：http://127.0.0.1:8000/health

---

## 接口说明

### `POST /triage/start` —— 开始问诊

**请求：**

```json
{ "user_input": "我发热两天了，还一直咳嗽" }
```

**响应：**

```json
{
  "session_id": "abc-123",
  "symptoms": ["发热", "咳嗽"],
  "missing_fields": ["最高体温", "是否呼吸困难"],
  "next_question": "请问最高体温是多少？有没有呼吸困难？",
  "risk_level": "low",
  "red_flags": []
}
```

### `POST /triage/continue` —— 继续追问

**请求：**

```json
{ "session_id": "abc-123", "user_input": "38.5 度，没有呼吸困难" }
```

**响应：**

```json
{
  "session_id": "abc-123",
  "updated_summary": "患者发热两天，最高体温 38.5°C，伴咳嗽，无呼吸困难",
  "symptoms": ["发热", "咳嗽"],
  "missing_fields": ["症状持续时间", "是否有咳痰"],
  "next_question": "咳嗽有痰吗？症状从什么时候开始的？",
  "risk_level": "low",
  "red_flags": [],
  "need_more_info": true,
  "stage": "collecting_info",
  "confirmed_facts": { "main_symptoms": ["发热", "咳嗽"], "max_temperature": "38.5C", "dyspnea": false },
  "uncertain_facts": ["症状持续时间", "是否有咳痰"]
}
```

### `POST /triage/evaluate` —— 生成分诊建议

**请求：**

```json
{ "session_id": "abc-123" }
```

**响应：**

```json
{
  "summary": "患者发热两天...",
  "risk_level": "low",
  "red_flags": [],
  "department": "呼吸内科",
  "advice": "建议前往呼吸内科就诊，如出现呼吸困难或高热不退请及时急诊。",
  "references": ["fever.md", "cough.md"]
}
```

---

## 技术栈

| 分类 | 技术 | 用途 |
|------|------|------|
| Web 框架 | FastAPI | HTTP 接口 |
| 数据校验 | Pydantic | 请求/响应模型 |
| LLM | OpenAI 兼容 SDK（默认 DeepSeek） | 症状抽取、风险判断、分诊建议 |
| 流程编排 | LangGraph | 三条问诊链路的节点编排 |
| 会话存储 | Redis（自动降级内存） | 多轮问诊状态维护 |
| 向量检索 | ChromaDB + text2vec-base-chinese | 医学知识库 RAG |
| 测试 | pytest | 接口/服务/工具/RAG 全覆盖 |

---

## 运行测试

```bash
python -m pytest
```

测试覆盖的关键场景：
- 三条问诊接口完整流程
- 高风险输入（胸痛、喘不上气）正确识别
- 无效 session_id 返回 404
- 高风险 session 后续不降级
- LLM 调用失败时的规则兜底
- 知识库检索返回结构和内容
- 科室推荐逻辑（高风险 → 急诊科）

---

## 下一步计划

按优先级排列：

1. **清理配置安全** —— 确保没有硬编码的 API Key 或密码
2. **完善 Redis 降级** —— 补充 Redis 恢复后自动切回的逻辑
3. **RAG 评估体系** —— 建评估集，测 recall@k 和 references 准确率
4. **知识库扩充** —— 补全儿科、妇产、老年等专科内容
5. **监控与追踪** —— 接好 LangSmith，统计各节点耗时和成功率

---

## 项目定位

**doctorTing 是什么：**
- LLM Agent 工程化的实战 Demo
- 医疗场景安全边界设计的参考实现
- RAG + Function Calling + 会话管理 + 流程编排的综合展示

**doctorTing 不是什么：**
- 医疗诊断系统
- 处方系统
- 可直接替代医生的线上服务
- 完整的医院 HIS/EMR 系统