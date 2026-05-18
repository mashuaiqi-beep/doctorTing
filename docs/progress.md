# 项目进度记录

## 当前阶段

当前项目处于：

```text
Agent MVP 增强阶段：核心接口稳定，ToolService 和 ChromaDB RAG 已接入，下一步重点是配置安全、Redis session、LangGraph 编排和评估体系。
```

项目已经从“能跑的 FastAPI + LLM Demo”推进到“具备工具层和知识检索能力的医疗分诊 Agent 雏形”。

## 已完成

### 1. 项目骨架

已经完成目录拆分：

- `app/api`
- `app/schema`
- `app/service`
- `app/core`
- `app/agent`
- `app/model`
- `app/tools`
- `app/utils`
- `app/scripts`
- `data/knowledge`
- `tests`
- `docs`

### 2. FastAPI 入口

已经具备：

- `FastAPI` 主应用
- 路由注册
- `/`
- `/health`
- Swagger 文档 `/docs`

项目可以作为 Web 服务启动。

### 3. 三条核心接口

当前已经实现：

- `POST /triage/start`
- `POST /triage/continue`
- `POST /triage/evaluate`

当前主链路包括：

1. API 接收请求。
2. Pydantic 校验请求体和响应体。
3. `TriageService` 编排业务。
4. `LLMService` 调用大模型。
5. `RiskControlService` 做规则兜底。
6. `ToolService` 调用红旗检查、知识检索和科室推荐工具。
7. `SessionStore` 保存会话。
8. API 返回结构化结果。

### 4. 大模型调用

已经完成：

- 使用 OpenAI SDK 兼容接口。
- 支持配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。
- 使用 `temperature=0` 提高结构化输出稳定性。
- 使用 JSON 解析兜底函数处理模型输出。
- LLM 调用失败时返回稳定 fallback。

### 5. 风险判断

已经完成：

- `risk_rules.py`
- `risk_control_service.py`
- 明确红旗关键词匹配
- LLM / Function Calling 方式的红旗症状语义判断
- 规则和 LLM 风险结果合并
- 高风险 session 后续不降级

合并策略：

- 规则命中高风险，则最终高风险。
- LLM 判断高风险，则最终高风险。
- LLM 调用失败时，回退到规则结果。

### 6. 会话状态

当前使用内存版 `SessionStore` 保存：

- `session_id`
- 用户消息历史
- 症状列表
- 缺失字段
- 下一轮问题
- 风险等级
- 红旗症状
- 摘要
- 创建时间
- 更新时间

同时已经有 `RedisSessionStore` 雏形，后续可通过工厂模式切换。

### 7. ToolService 工具层

已经完成工具层入口：

- `extract_symptoms`
- `check_red_flags`
- `search_knowledge`
- `book_appointment`

当前状态：

- 红旗检查已使用 OpenAI-compatible function calling schema。
- 知识检索已封装为工具服务。
- 科室推荐已封装为模拟挂号工具。
- 主流程当前仍以后端编排为主，后续可升级为 LangGraph/LLM 自主选择工具。

### 8. RAG 知识检索

已经完成：

- 本地 Markdown 医疗知识库。
- 轻量关键词检索工具。
- ChromaDB 向量知识库服务。
- `build_knowledge_index.py` 重建索引脚本。
- Markdown 段落切 chunk。
- metadata 保存 `source`、`title`、`chunk_index`。
- `/triage/evaluate` 阶段调用知识检索。
- 最终响应返回 `references`。

当前知识库示例：

- `fever.md`
- `cough.md`
- `chest_pain.md`

### 9. 科室推荐

已经完成模拟挂号工具：

- 高风险直接推荐急诊科。
- 低风险根据症状规则推荐呼吸内科、发热门诊、消化内科、神经内科等。
- 无法匹配时回退到全科医学科。

### 10. 自动化测试

当前已经覆盖：

- 三条核心接口完整流程。
- 高风险输入识别。
- 无效 `session_id` 返回 404。
- LLM 红旗判断失败时规则仍然生效。
- 高风险 session 后续不降级。
- 模拟挂号工具。
- 本地知识检索工具。
- ChromaDB 索引构建和检索。

## 当前存在的问题

### 1. 配置安全需要清理

当前 `app/core/config.py` 里还有默认配置值，后续应改成完全从环境变量读取，并增加 `.env.example`。

### 2. 内存 SessionStore 不适合生产

当前内存存储适合 Demo，但存在限制：

- 服务重启后会话丢失。
- 多进程或多实例无法共享会话。
- 无自动过期机制。

后续应通过配置切换到 Redis。

### 3. RAG 还缺少评估体系

虽然 ChromaDB 检索已经接入，但还缺少系统评估：

- recall@k
- references 命中率
- 检索结果是否真正被最终建议使用
- 不同 query 对知识库的覆盖情况

### 4. 知识库内容较少

`data/knowledge` 当前适合作为 RAG 起步素材，但还不足以支撑完整医疗问诊展示。

### 5. LangGraph 仍是预留

`agent/triage_graph.py` 当前是结构示例，还没有接入主服务链路。

### 6. 数据库模型仍是预留

`model/` 目录当前只是后续扩展入口，尚未正式接入业务链路。

## 下一步计划

### 第一优先级

- 清理默认 API key 和敏感配置。
- 增加 `.env.example`。
- 同步 README 与实际代码状态。
- 稳定当前测试。
- 增加 RAG 返回结果的更多断言。

### 第二优先级

- 增加 session store 工厂。
- 支持 `SESSION_STORE_TYPE=memory|redis`。
- 完善 Redis 相关测试。
- 扩充红旗症状规则。
- 增强 Prompt 和兜底文案。

### 第三优先级

- 扩充 `data/knowledge`。
- 统一 Markdown 知识文档结构。
- 建立 RAG 评估集。
- 统计 recall@k、references 命中率和 JSON valid rate。

### 第四优先级

- 接入 `LangGraph`。
- 将 `start/continue/evaluate` 拆成节点。
- 实现高风险急诊分支。
- 接入 `LangSmith` 做调用链路观测。

### 第五优先级

- 增加数据库长期问诊记录。
- 保存最终 evaluate 结果。
- 支持根据 `session_id` 查询历史问诊。

## 当前阶段总结

项目已经具备一个 Agent 项目的核心雏形：

```text
FastAPI 接口
  + 多轮 session
  + LLM 结构化输出
  + 红旗风险控制
  + ToolService
  + ChromaDB RAG
  + 科室推荐
  + pytest 测试
```

下一阶段最值得做的是：

```text
配置安全
  -> Redis session
  -> RAG 评估
  -> LangGraph 编排
```

这样项目会从“功能能跑”继续升级为“更接近真实 Agent 工程实践”的面试项目。
