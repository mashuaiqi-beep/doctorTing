# 项目规划

## 项目名称

医疗问诊分诊 Agent

## 项目目标

做一个小型但完整的医疗 Agent Demo，用来展示以下能力：

- 设计 Agent 工作流
- 将 LLM 接入真实业务
- 输出稳定的结构化结果
- 用后端工程方式封装 API
- 后续结合 `RAG`、`LangGraph` 和工具调用

## 为什么这个项目适合 Agent 实习展示

这个项目足够小，容易在较短时间内完成，同时覆盖面试官容易关注的能力点：

- `FastAPI`
- `Pydantic`
- Structured Output
- 风险规则兜底
- 会话状态管理
- 后续可扩展到 `LangGraph`
- 后续可扩展到 `RAG`
- 后续可接入 Agent 可观测

相比“大而全”的医疗平台，这个项目更适合作为高质量作品集项目。

## 用户场景

用户输入：

```text
发热两天，咳嗽，胸口有点闷
```

Agent 需要完成：

1. 提取已知症状。
2. 决定是否需要继续追问。
3. 识别高风险信号。
4. 输出分诊建议。
5. 后续可以检索知识库作为依据。

## 技术方案

### 1. 后端接口

使用：

- `FastAPI`
- `Pydantic`

职责：

- 提供外部访问接口
- 管理请求和响应结构
- 校验参数

### 2. 模型调用

使用：

- `OpenAI SDK` 或兼容模型接口

职责：

- 理解用户输入
- 生成追问内容
- 输出结构化建议
- 识别口语化红旗症状

### 3. 规则控制

使用：

- Python 规则模块

职责：

- 识别红旗症状
- 设定风险等级
- 保证医疗安全边界

### 4. 会话存储

当前：

- 内存 `SessionStore`

后续：

- `Redis`
- `PostgreSQL`

职责：

- 保存问诊记录
- 保存症状摘要
- 保存风险等级和红旗症状

### 5. 知识增强

后续使用：

- 本地知识库检索
- `RAG`
- `pgvector`

职责：

- 从小型医疗知识库中检索文档
- 给模型补充事实依据
- 降低幻觉

### 6. Agent 编排

后续使用：

- `LangGraph`

职责：

- 串联问诊流程
- 管理状态流转
- 把节点拆成可解释步骤

### 7. 调试与观测

后续使用：

- `LangSmith`

职责：

- 观察每个节点执行过程
- 调试提示词和工具调用
- 展示 Agent trace

## LangGraph 节点规划

建议后续拆成 4 个节点：

- `collect_info`：抽取症状和缺失信息。
- `check_risk`：调用规则和 LLM 判断红旗症状。
- `retrieve_knowledge`：根据症状检索知识库。
- `generate_advice`：结合上下文输出结构化分诊结果。

## Tool Calling 规划

后续只做 3 个工具即可：

- `extract_symptoms`：提取症状、持续时间、严重程度。
- `check_red_flags`：检查胸痛、呼吸困难、高热不退、意识异常等风险。
- `search_medical_knowledge`：根据症状检索知识文档，返回证据片段与来源。

## 数据表规划

后续建议只做 2 张核心表：

`consultations`：

- `id`
- `session_id`
- `user_input`
- `symptom_summary`
- `risk_level`
- `advice`
- `created_at`

`knowledge_docs`：

- `id`
- `title`
- `content`
- `source`
- `embedding`

## API 设计

### `POST /triage/start`

输入：

- 用户首轮主诉

输出：

- 抽取结果
- 下一轮追问
- 风险等级

### `POST /triage/continue`

输入：

- 会话 ID
- 用户补充回答

输出：

- 更新后的问诊状态
- 下一轮追问或结束判断

### `POST /triage/evaluate`

输入：

- 会话 ID

输出：

- 结构化分诊建议
- 风险等级
- 推荐科室
- 注意事项

## 开发顺序

### 第 1 阶段：稳定 MVP

- 修复文档编码
- 同步 README 和当前代码状态
- 补充三接口自动化测试
- 稳定 `/triage/start`、`/triage/continue`、`/triage/evaluate`

### 第 2 阶段：增强问诊质量

- 扩充红旗症状规则
- 增强异常兜底
- 优化 Prompt
- 增加更多测试场景

### 第 3 阶段：知识检索

- 整理 `data/knowledge`
- 做本地知识检索 MVP
- 将检索结果接入 `evaluate`
- 再升级到 pgvector

### 第 4 阶段：Agent 工作流

- 用 LangGraph 重构当前 service 流程
- 增加节点状态
- 接入 LangSmith 观测

## 交付标准

项目完成时至少满足：

- 能跑通一次完整问诊。
- 能输出 JSON 格式建议。
- 能识别明显红旗症状。
- 能运行自动化测试。
- 能在 README 中讲清楚架构、边界和亮点。

## 简历描述模板

- 基于 `FastAPI` 和 OpenAI 兼容接口实现医疗问诊分诊 Agent，支持多轮追问、风险识别和结构化输出。
- 设计“规则兜底 + LLM 语义判断”的红旗症状识别链路，降低医疗场景中模型漏判风险。
- 使用会话状态管理串联多轮问诊，并为后续 LangGraph、RAG 和可观测链路预留扩展点。
