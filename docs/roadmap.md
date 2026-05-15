# doctorTing 详细路线图

## 项目终极目标

将 doctorTing 从一个可运行的 FastAPI + LLM Demo，逐步建设为一个具备工具调用、知识检索、工作流编排、短长期记忆、可观测和评估能力的医疗问诊分诊 Agent。

项目边界始终保持清晰：

- 不替代医生诊断。
- 不直接开处方。
- 不承诺医疗结论。
- 重点展示 Agent 工程能力和医疗安全边界设计。

---

## 当前基线

当前已经完成：

- `POST /triage/start`
- `POST /triage/continue`
- `POST /triage/evaluate`
- FastAPI 路由层
- Pydantic 请求/响应模型
- LLM 结构化输出
- JSON 解析兜底
- 规则 + LLM 双层红旗症状判断
- 内存版 `SessionStore`
- 基础测试用例
- ToolService / RedisSessionStore / RAG 工具雏形

当前最重要的原则：

```text
先把已有主链路稳定，再逐步接入 Tool Calling、RAG、LangGraph、Redis 和 Eval。
```

---

## Phase 0 - 稳定 MVP 基线

### 目标

让当前三条核心接口稳定、可测、可演示。

这一阶段不是继续堆功能，而是把已有主链路打磨成一个可靠的 MVP。

### 使用技术

- `FastAPI`
- `Pydantic`
- `pytest`
- `fastapi.testclient`
- 环境变量配置
- 内存版 `SessionStore`
- JSON 解析兜底

### 实现业务

- 用户输入症状。
- 系统开始首轮问诊。
- 系统基于 `session_id` 继续追问。
- 系统生成最终分诊建议。
- 系统识别红旗症状。
- 系统维护多轮问诊上下文。

### 具体任务

1. 清理明文 API Key 和临时脚本。
2. 修复临时代码、重复 return、不可达代码。
3. 保证 `python -m pytest` 能跑通。
4. 补充异常测试。
5. 完善 README 和接口示例。
6. 明确医疗安全边界：不诊断、不开药、不替代医生。

### 测试覆盖

- 普通低风险输入。
- 高风险输入。
- 信息不足输入。
- 无效 `session_id`。
- LLM 返回非法 JSON。
- LLM 调用失败。
- 高风险后续不能被降级。

### 完成标志

- `python -m pytest` 全绿。
- 三个接口可以从 Swagger 完整跑一遍。
- README 能让别人独立启动项目。
- 项目没有明文密钥。

### 面试表达

> 我先用 FastAPI 和 Pydantic 搭建三条核心问诊接口，并用 pytest 覆盖主流程和异常场景，保证 Agent Demo 不是只能手动跑通，而是有可回归验证的后端服务。

---

## Phase 1 - Tool Calling 工具层

### 目标

让项目从普通 LLM 调用升级为具备工具能力的 Agent。

### 使用技术

- OpenAI-compatible Tool Calling
- Function Schema
- JSON Schema
- 本地 Python 工具函数
- `ToolService` 封装

### 实现业务

将问诊流程中的能力拆成工具：

- 症状抽取工具。
- 红旗症状检查工具。
- 知识检索工具。
- 模拟挂号工具。

### 工具职责

`extract_symptoms`

- 输入：用户自然语言描述。
- 输出：结构化症状列表。
- 业务价值：把自由文本转成后续节点可用的结构化字段。

`check_red_flags`

- 输入：用户描述和症状列表。
- 输出：是否有红旗症状、风险等级、原因。
- 业务价值：识别胸痛、呼吸困难、意识模糊等高风险信号。

`search_knowledge`

- 输入：症状或摘要 query。
- 输出：相关知识片段和来源。
- 业务价值：为后续 RAG 做准备。

`book_appointment`

- 输入：症状和风险等级。
- 输出：推荐科室、挂号类型、提示文案。
- 业务价值：模拟医疗服务后续动作。

### 推荐分层

```text
app/tools/
  extract_symptoms.py
  check_red_flags.py
  search_knowledge.py
  book_appointment.py

app/service/tool_service.py
```

`triage_service.py` 不直接关心工具细节，只调用 `ToolService`。

### 关键说明

完整 Tool Calling 不只是让 LLM 按 schema 返回 JSON。

更严谨的流程是：

```text
LLM 选择要调用的工具
        ↓
后端解析 tool_call
        ↓
后端执行本地工具函数
        ↓
工具结果写回业务状态
```

### 完成标志

- `ToolService` 能统一调用 4 个工具。
- `triage_service.py` 不直接依赖具体工具实现。
- `/triage/evaluate` 能使用 `book_appointment` 推荐科室。
- `/triage/evaluate` 能使用 `search_knowledge` 返回 `references`。

### 面试表达

> 我把症状抽取、风险识别、知识检索、科室推荐拆成工具，并通过 ToolService 统一封装，为后续 LangGraph 编排和多 Agent 协作打基础。

---

## Phase 2 - 轻量 RAG 知识检索

### 目标

先做一个不上向量库的 RAG MVP，让 `/triage/evaluate` 的 `references` 真正有内容。

### 使用技术

- Markdown 知识库
- 本地文件读取
- 关键词检索
- 简单文本匹配
- Prompt 注入检索结果

### 实现业务

- 根据症状检索知识库。
- 把知识片段提供给最终分诊建议生成。
- 在最终响应中返回 `references`。

### 当前素材

```text
data/knowledge/
  fever.md
  cough.md
  chest_pain.md
```

### 推荐知识文档格式

```markdown
# 胸痛

## 常见原因

...

## 红旗症状

- 胸痛伴呼吸困难
- 胸痛伴大汗
- 胸痛放射至左肩或下颌

## 建议科室

急诊科、心内科

## 安全建议

...
```

### 具体任务

1. 扩充 `data/knowledge` 文档。
2. 统一每篇 Markdown 的结构。
3. 实现本地 Markdown loader。
4. 实现关键词检索。
5. 在 evaluate 阶段注入检索结果。
6. 让响应里的 `references` 返回文档来源。

### 完成标志

- 输入“胸痛”时能检索到 `chest_pain.md`。
- 输入“发热”时能检索到 `fever.md`。
- `/triage/evaluate` 返回的 `references` 不再为空。
- 最终 `advice` 会参考检索内容。

### 面试表达

> 我先用本地 Markdown 做轻量 RAG，通过症状关键词检索相关医学知识，并在最终分诊建议中返回 references，避免模型完全凭空生成。

---

## Phase 3 - 向量 RAG 升级

### 目标

从关键词检索升级到语义检索，解决用户口语表达和文档关键词不完全匹配的问题。

### 使用技术

- `ChromaDB` 或 `FAISS`
- Embedding model
- 文档切分
- 向量索引持久化
- 可选：LangChain Document Loader

建议先用 `ChromaDB`，比一开始上 `PostgreSQL + pgvector` 更轻。

### 实现业务

示例：

```text
用户：胸口压着难受，喘不过气
  ↓
生成 embedding
  ↓
向量检索
  ↓
命中胸痛/呼吸困难相关知识
  ↓
生成更可靠的分诊建议
```

### 具体任务

1. 读取 `data/knowledge/*.md`。
2. 将文档切分成 chunk。
3. 对 chunk 生成 embedding。
4. 存入 ChromaDB 或 FAISS。
5. 实现 `search_knowledge(query, top_k)`。
6. 替换 Phase 2 的关键词检索。

### 完成标志

- 用户没有直接说“胸痛”，说“胸口压着难受”，也能检索到胸痛文档。
- `/triage/evaluate` 能引用检索结果。
- `references` 返回具体文档名或 chunk 来源。

### 面试表达

> 我将本地关键词检索升级为向量检索，解决用户口语化表达和知识文档关键词不完全匹配的问题。

---

## Phase 4 - Redis 短期记忆

### 目标

把内存 session 替换成可共享、可过期的 Redis session。

### 使用技术

- Redis
- `redis-py`
- JSON serialization
- TTL
- SessionStore 抽象
- 工厂模式

### 实现业务

- 问诊会话不再只存在 Python 进程内存里。
- 服务重启或多实例部署时可以共享会话。
- 会话可以自动过期。

### 当前内存版问题

- 服务重启丢失 session。
- 多进程不共享 session。
- 不能自动过期。

### Redis 设计

```text
key:
triage:session:{session_id}

value:
{
  "session_id": "...",
  "messages": [...],
  "symptoms": [...],
  "risk_level": "low",
  "red_flags": [...],
  "summary": "..."
}

ttl:
24 小时
```

### 具体任务

1. 保留内存版 `SessionStore`。
2. 完善 `RedisSessionStore`。
3. 增加 `SESSION_STORE_TYPE=memory/redis`。
4. 实现 `create_session_store()` 工厂。
5. 测试 memory 和 redis 两种模式。

### 完成标志

- 配置 `SESSION_STORE_TYPE=memory` 时使用内存。
- 配置 `SESSION_STORE_TYPE=redis` 时使用 Redis。
- `TriageService` 不关心底层存储实现。
- Redis 中能看到 `triage:session:{session_id}`。

### 面试表达

> MVP 阶段我用内存字典快速打通多轮问诊，后续用 Redis 保存短期会话状态，支持 TTL、多进程共享和更接近生产的部署方式。

---

## Phase 5 - 数据库长期记忆

### 目标

保存最终问诊记录，不只是保存临时 session。

### 使用技术

- SQLAlchemy
- SQLite 或 PostgreSQL
- ORM Model
- 可选：Alembic

### 实现业务

问诊完成后保存：

- 用户输入历史。
- 症状摘要。
- 风险等级。
- 红旗症状。
- 推荐科室。
- 最终建议。
- 创建时间。

### 数据表建议

```text
consultations
- id
- session_id
- summary
- symptoms
- risk_level
- red_flags
- department
- advice
- created_at
```

后续如果做用户系统，再加：

```text
users
medical_profiles
allergies
medical_history
```

### 完成标志

- 调用 `/triage/evaluate` 后，最终结果写入数据库。
- 可以根据 `session_id` 查询历史问诊记录。
- Redis 存短期上下文，数据库存长期结果。

### 面试表达

> Redis 存短期上下文，数据库存长期问诊记录。我把短期记忆和长期记忆分开，避免把临时状态和业务历史混在一起。

---

## Phase 6 - LangGraph 编排

### 目标

把现在手写的 service 调用链，重构成 Agent 工作流。

### 使用技术

- LangGraph
- `StateGraph`
- `TypedDict` State
- Node
- Conditional Edge

### 实现业务

当前流程：

```text
extract_triage_info
check_risk
search_knowledge
evaluate
```

重构为图节点：

```text
collect_info_node
check_risk_node
retrieve_knowledge_node
generate_question_node
generate_advice_node
```

### 推荐图结构

```text
start
  ↓
collect_info
  ↓
check_risk
  ↓
if high risk:
    emergency_advice
else:
    retrieve_knowledge
      ↓
    generate_advice
```

高风险短路很重要：

```text
胸痛 + 呼吸困难
  ↓
直接急诊建议
  ↓
不需要慢慢 RAG
```

### 具体任务

1. 定义 `TriageState`。
2. 实现 `collect_info_node`。
3. 实现 `check_risk_node`。
4. 实现 `retrieve_knowledge_node`。
5. 实现 `generate_question_node` 和 `generate_advice_node`。
6. 接入条件边，高风险短路。
7. 让 `TriageService` 调用 `graph.invoke(state)`。

### 完成标志

- `triage_graph.py` 不再只是示例。
- `TriageService` 主流程可以走 LangGraph。
- 一次问诊可以看到 state 在节点间流转。
- 高风险输入能走紧急建议路径。

### 面试表达

> 我用 LangGraph 将问诊流程拆成多个节点，并通过条件边实现高风险短路，让医疗场景中的安全优先级体现在 Agent 编排里。

---

## Phase 7 - LangSmith 可观测

### 目标

让每次 LLM 调用和 Agent 节点可追踪。

### 使用技术

- LangSmith
- `LANGCHAIN_API_KEY`
- `LANGCHAIN_TRACING_V2`
- Trace
- Run metadata

### 实现业务

- 追踪一次问诊经过了哪些节点。
- 记录每个节点耗时。
- 记录 LLM 输入输出。
- 记录 token 消耗。
- 记录 fallback 是否发生。

### 具体任务

1. 配置 LangSmith 环境变量。
2. 给关键节点加 trace 名称。
3. 给 start/continue/evaluate 打 metadata。
4. 观察 token、latency、错误率。

### 完成标志

- LangSmith dashboard 能看到一次完整问诊链路。
- 能区分 `collect_info`、`check_risk`、`retrieve_knowledge`、`evaluate` 等节点。
- 能看到每次 LLM 调用的输入、输出、耗时和错误。

### 面试表达

> 我接入 LangSmith 追踪 Agent 调用链路，用于定位 Prompt 问题、分析延迟和 token 成本。

---

## Phase 8 - Eval 评估体系

### 目标

不要只靠“看起来还行”，而是用数据评估 Agent 能力。

### 使用技术

- `pytest`
- JSONL 评估集
- 批量调用脚本
- 准确率/召回率
- 可选：LangSmith Dataset

### 实现业务

评估两个核心能力：

- 红旗症状识别。
- 分诊科室推荐。

### 评估样本示例

```json
{
  "input": "我胸口压着难受，还喘不上气",
  "expected_risk_level": "high",
  "expected_red_flags": ["胸痛", "呼吸困难"],
  "expected_department": "急诊科"
}
```

### 指标

- `risk_level accuracy`
- `red_flags recall`
- `department accuracy`
- `JSON valid rate`
- `fallback rate`

### 具体任务

1. 构建 20-50 条红旗症状样本。
2. 构建 20-50 条分诊科室样本。
3. 写批量评估脚本。
4. 计算准确率、召回率和 JSON 合法率。
5. 每次改 Prompt/规则/RAG 后运行评估。

### 完成标志

- 每次改 Prompt 或规则后，可以用数字判断效果变化。
- 能识别假阴性问题，例如高风险被误判为低风险。

### 面试表达

> 我为红旗症状识别和科室推荐构建了小型评估集，用准确率和召回率衡量 Prompt 与规则优化效果，而不是只凭主观体验判断。

---

## Phase 9 - 多 Agent 协作

### 目标

把一个大 Agent 拆成多个职责明确的小 Agent。

### 使用技术

- LangGraph
- 多节点 Agent
- 角色 Prompt
- 可选：LLM-as-judge

### 实现业务

拆分角色：

- 问诊 Agent：负责追问信息。
- 风控 Agent：负责识别红旗风险。
- 分诊 Agent：负责推荐科室和建议。
- 安全审核 Agent：检查输出是否越界。

### 推荐流程

```text
问诊 Agent
  ↓
风控 Agent
  ↓
RAG
  ↓
分诊 Agent
  ↓
安全审核 Agent
```

### 完成标志

- Trace 里能看到多个 Agent 独立工作。
- 每个 Agent 有明确输入输出。
- 最终建议经过安全审核。
- 安全审核能拦截诊断、开药、夸大承诺等越界输出。

### 面试表达

> 我将单体 Agent 拆成问诊、风控、分诊和安全审核多个角色，通过 LangGraph 编排协作，提高职责清晰度和医疗安全性。

---

## 推荐执行顺序

考虑当前项目状态，建议按这个顺序推进：

```text
Phase 0：先让测试和代码干净
Phase 1：完善 Tool Calling
Phase 2：接入本地关键词 RAG
Phase 3：升级向量 RAG
Phase 6：接 LangGraph
Phase 4：Redis 短期记忆
Phase 5：数据库长期记忆
Phase 7：LangSmith
Phase 8：Eval
Phase 9：多 Agent
```

Redis 很重要，但对这个项目的求职展示来说，RAG 和 LangGraph 更能体现 Agent 能力。Redis 更偏工程稳定性，可以在主 Agent 能力成型后补上。

---

## 总路线

```text
稳定三接口
  ↓
工具化
  ↓
知识增强
  ↓
图编排
  ↓
记忆持久化
  ↓
观测与评估
  ↓
多 Agent 协作
```

最终目标是让项目从：

```text
普通 FastAPI + LLM Demo
```

逐步升级为：

```text
可观测、可评估、有工具、有知识库、有工作流编排的医疗分诊 Agent
```
