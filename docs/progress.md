# 项目进度记录

## 当前阶段

当前项目处于：

```text
MVP 稳定阶段：三条核心接口已经具备真实逻辑，正在补文档、测试和稳定性。
```

核心目标是让项目从“能跑”变成“可信、可讲、可演示”。

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

### 2. FastAPI 入口

已经具备：

- `FastAPI` 主应用
- 路由注册
- `/`
- `/health`

项目可以作为 Web 服务启动。

### 3. 三条核心接口

当前已经实现：

- `POST /triage/start`
- `POST /triage/continue`
- `POST /triage/evaluate`

当前主链路包括：

1. API 接收请求。
2. Service 处理业务。
3. LLM Service 调用大模型。
4. Risk Control Service 做规则兜底。
5. SessionStore 保存会话。
6. API 返回结构化结果。

### 4. 大模型调用

已经完成：

- 使用 OpenAI SDK 兼容接口。
- 通过环境变量配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。
- 使用 `temperature=0` 提高结构化输出稳定性。
- 使用 JSON 解析兜底函数处理模型输出。

### 5. 风险判断

已经完成：

- `risk_rules.py`
- `risk_control_service.py`
- 规则关键词匹配
- LLM 红旗症状语义判断
- 规则和 LLM 风险结果合并

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

## 当前存在的问题

### 1. 测试仍需持续补充

当前目标是先覆盖三条核心接口和服务层关键逻辑，后续还需要继续补：

- 模型异常
- JSON 解析异常
- 高风险合并
- 无效 `session_id`
- 信息不足输入

### 2. 内存 SessionStore 不适合生产

当前内存存储适合 Demo，但存在限制：

- 服务重启后会话丢失。
- 多进程或多实例无法共享会话。
- 无法长期追踪问诊记录。

后续可以迁移到 Redis 或数据库。

### 3. 知识库内容较少

`data/knowledge` 当前只有少量示例文档，适合作为 RAG 起步素材，但还不足以支撑完整知识增强。

### 4. LangGraph 仍是预留

`agent/triage_graph.py` 当前是结构示例，还没有接入主服务链路。

### 5. 数据库模型仍是预留

`model/` 目录当前只是后续扩展入口，尚未正式接入业务链路。

## 下一步计划

### 第一优先级

- 修复文档编码。
- 同步 README 与实际代码状态。
- 补充接口自动化测试。
- 稳定当前三条接口。

### 第二优先级

- 扩充红旗症状规则。
- 增强 Prompt 和兜底文案。
- 补充更多异常测试。
- 优化会话摘要质量。

### 第三优先级

- 整理本地知识库。
- 实现本地知识检索 MVP。
- 在 `/triage/evaluate` 中返回 `references`。

### 第四优先级

- 接入 `LangGraph`。
- 接入 `RAG`。
- 接入 `LangSmith`。

## 当前阶段总结

项目已经从规划阶段进入可运行 Demo 阶段。现在最重要的工作是提高可维护性和可演示性：

- 文档可读。
- 接口稳定。
- 测试能跑。
- 边界清楚。
- 主链路能解释。
