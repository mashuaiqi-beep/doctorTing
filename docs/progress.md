# 项目进度记录

## 当前阶段

截至 2026-05-19，项目已经进入“Agent MVP 持续增强”阶段。

相比最初的 FastAPI + LLM Demo，当前仓库已经补齐了几块更像真实工程的能力：

- `/triage/start` 已经通过 LangGraph 编排
- 会话默认落到 Redis，而不再是纯内存
- 引入了 ChromaDB 向量检索和 `references` 返回
- 增加了静态前端工作台，用户可以直接在首页完成一轮问诊

一句话概括：现在它已经不是单纯的接口样例，而是一个带前端、带状态、带检索的医疗分诊 Agent 雏形。

## 已完成

### 1. 应用骨架

项目当前已经形成比较清晰的模块分层：

- `app/api`：HTTP 接口
- `app/schema`：Pydantic 请求响应模型
- `app/service`：业务服务、LLM、Redis session、RAG
- `app/core`：配置、Prompt、风险规则
- `app/agent`：LangGraph 编排
- `app/tools`：工具调用入口
- `app/static`：前端页面
- `app/scripts`：知识索引构建
- `tests`：自动化测试

### 2. 核心接口

三条主接口已经具备稳定结构：

- `POST /triage/start`
- `POST /triage/continue`
- `POST /triage/evaluate`

其中：

- `start` 负责首轮抽取、风险判断、创建 session
- `continue` 负责补充追问、更新摘要和风险
- `evaluate` 负责知识检索、科室推荐和最终建议生成

### 3. LangGraph 已接入真实链路

[app/agent/triage_graph.py](/E:/py/doctorTing/app/agent/triage_graph.py) 不再只是预留结构，已经接入 `TriageService.start_triage()`。

当前图内节点顺序为：

1. `extract_info`
2. `check_rule_risk`
3. `check_llm_risk`
4. `merge_risk`
5. `save_session`
6. `build_response`

这说明 LangGraph 已经开始承担主流程编排职责，只是覆盖范围还局限在首轮问诊。

### 4. Redis Session 已切入主流程

当前 [app/service/triage_service.py](/E:/py/doctorTing/app/service/triage_service.py) 默认实例化的是 [app/service/redis_session_store.py](/E:/py/doctorTing/app/service/redis_session_store.py)。

当前 session 能保存的信息包括：

- `session_id`
- `messages`
- `symptoms`
- `missing_fields`
- `next_question`
- `risk_level`
- `red_flags`
- `summary`
- `retrieval_query`
- `state_history`
- `created_at`
- `updated_at`

相比早期的内存版，这一步更接近真实多轮问诊场景。

### 5. 风险控制

当前已经形成“规则兜底 + LLM 语义识别”的双层风险判断：

- 明确红旗词由规则层兜底
- 口语化表达由 LLM 层补充识别
- 合并策略偏保守
- 高风险会话后续不会降级

这部分是目前项目最完整、也最像医疗安全工程意识的一块。

### 6. RAG 检索

当前知识检索链路已经打通：

- `data/knowledge/*.md` 作为知识源
- `VectorKnowledgeService` 负责向量化与检索
- `build_knowledge_index.py` 负责重建索引
- `/triage/evaluate` 返回 `references`

这意味着最终建议已经不只是“裸 LLM 输出”，而是能显式带出参考来源。

### 7. 前端工作台

根路径 `/` 现在会返回静态页面，而不是简单文本响应。

当前前端已经支持：

- 发起首轮问诊
- 查看系统追问
- 展示风险等级和红旗症状
- 查看建议科室、摘要、建议文案和参考依据

这对项目演示和面试展示帮助很大。

### 8. 自动化测试

现有测试已经覆盖到几个关键面：

- API 全流程
- 高风险输入识别
- 无效 session 的 404
- 高风险 session 不降级
- ChromaDB 索引构建
- 向量检索返回结构

说明项目已经开始具备“改代码时有基本回归保护”的状态。

## 当前风险和不足

### 1. 配置安全仍需清理

[app/core/config.py](/E:/py/doctorTing/app/core/config.py) 里仍有默认的 API Key 和 Redis 连接串，这在文档层面必须明确标为待处理风险。

这一点比“功能缺没缺”更优先，因为它直接影响项目可公开性和安全性。

### 2. Redis 依赖已变成主流程前置条件

当前 `TriageService` 默认直接使用 Redis session store。

这意味着：

- 本地未启动 Redis 时，项目可能无法正常跑完整链路
- 文档需要明确这一依赖
- 代码后续最好补一个 `memory|redis` 可切换的工厂层

### 3. LangGraph 覆盖范围还不完整

虽然 `start` 已接入 LangGraph，但：

- `continue` 仍是普通 service 流程
- `evaluate` 仍是普通 service 流程
- 还没有条件分支、异常恢复、人工干预等更典型 Agent 图能力

### 4. RAG 仍缺评估体系

现在已经“接入了检索”，但还没有系统证明“检索质量足够好”：

- 没有 recall@k
- 没有 references 命中率评估
- 没有问诊建议质量对比
- 没有标准评测集

### 5. 知识库质量和规模还偏演示型

`data/knowledge/` 中已经有较多疾病文档，但整体仍更偏 demo 数据集，不适合被描述成“完整医学知识库”。

### 6. 数据持久化仍不完整

虽然 session 已经落 Redis，但：

- 还没有长期病例归档
- 没有数据库层的正式问诊记录模型
- `model/` 目录仍主要是预留扩展位

## 下一阶段建议

### 第一优先级

1. 清理硬编码敏感配置
2. 补齐 `.env.example` 与 README 的配置说明一致性
3. 为 Redis 不可用场景补充降级策略或可切换工厂
4. 跑通并稳定当前测试

### 第二优先级

1. 把 `continue` 和 `evaluate` 迁入 LangGraph
2. 增加高风险分支和急诊建议分支
3. 统一 session 状态字段定义

### 第三优先级

1. 建立 RAG 评估集
2. 补充召回和引用命中指标
3. 扩充知识库并统一 Markdown 结构

### 第四优先级

1. 引入 LangSmith 或其他链路观测
2. 增加数据库持久化
3. 支持历史问诊查询

## 当前结论

如果把项目成熟度粗略分层：

```text
阶段 1：能跑的接口 Demo
阶段 2：有状态、有工具、有检索的 Agent 雏形   <- 当前所在位置
阶段 3：可评估、可观测、可扩展的工程化 Agent
```

doctorTing 现在已经稳稳站在阶段 2，但距离“更完整的工程化 Agent”还差配置安全、评估体系和编排完整度这三块。
