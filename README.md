# Medical Triage Agent

一个面向 Agent 实习/求职展示的小型医疗问诊分诊 Demo。

项目目标不是替代医生诊断，也不是完整医院系统，而是用一个可运行的后端 MVP 展示：

- 多轮问诊
- 红旗症状识别
- 结构化 JSON 输出
- 会话状态管理
- 大模型接口调用
- 后续扩展到 LangGraph、RAG 和可观测链路的空间

## 当前状态

当前已经实现 3 个核心接口：

- `POST /triage/start`：开始问诊，抽取症状、发现缺失信息、生成追问，并判断风险。
- `POST /triage/continue`：基于 `session_id` 继续追问，更新会话状态。
- `POST /triage/evaluate`：基于完整会话生成最终分诊建议。

当前风险判断采用“规则兜底 + LLM 语义判断”的组合方式：

- 规则层匹配明确红旗词，如胸痛、胸闷、呼吸困难、意识模糊等。
- LLM 层识别用户的口语化表达，如“喘不上气”“胸口压着难受”。
- 合并时采用保守策略：规则或 LLM 任一判断为高风险，最终 `risk_level` 为 `high`。

## 技术栈

- 后端：`Python`、`FastAPI`、`Pydantic`
- 大模型：OpenAI SDK 兼容接口，默认配置为 DeepSeek 兼容地址
- 会话：内存版 `SessionStore`
- 结构化输出：Prompt 约束 JSON + JSON 解析兜底
- 风险控制：关键词规则 + LLM 语义识别
- 测试：`pytest`、`fastapi.testclient`

规划中但尚未正式接入生产链路：

- `LangGraph`
- `RAG`
- `PostgreSQL + pgvector`
- `Redis`
- `LangSmith`

## 启动方式

安装依赖：

```bash
pip install -r requirements.txt
```

配置环境变量：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
```

PowerShell 临时配置示例：

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
$env:OPENAI_BASE_URL="https://api.deepseek.com"
$env:OPENAI_MODEL="deepseek-v4-flash"
```

启动服务：

```bash
uvicorn app.main:app --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

运行测试：

```bash
python -m pytest
```

## 接口流程

### 1. 开始问诊

```http
POST /triage/start
```

请求：

```json
{
  "user_input": "我发热两天了，还一直咳嗽"
}
```

响应示例：

```json
{
  "session_id": "b9a6f7d2-2f30-45c2-a1e4-9a08c82f5e5b",
  "symptoms": ["发热", "咳嗽"],
  "missing_fields": ["最高体温", "是否呼吸困难"],
  "next_question": "请问最高体温是多少？有没有胸闷或呼吸困难？",
  "risk_level": "low",
  "red_flags": []
}
```

### 2. 继续问诊

`session_id` 来自 `/triage/start` 的返回结果。前端或调用方需要保存并传回。

```http
POST /triage/continue
```

请求：

```json
{
  "session_id": "b9a6f7d2-2f30-45c2-a1e4-9a08c82f5e5b",
  "user_input": "最高 38.5 度，没有呼吸困难"
}
```

响应示例：

```json
{
  "session_id": "b9a6f7d2-2f30-45c2-a1e4-9a08c82f5e5b",
  "updated_summary": "用户发热两天，最高体温 38.5 度，伴咳嗽，否认呼吸困难。",
  "next_question": "请问是否有咽痛、流涕或基础疾病？",
  "need_more_info": true
}
```

### 3. 生成分诊建议

```http
POST /triage/evaluate
```

请求：

```json
{
  "session_id": "b9a6f7d2-2f30-45c2-a1e4-9a08c82f5e5b"
}
```

响应示例：

```json
{
  "summary": "用户发热两天，最高体温 38.5 度，伴咳嗽，暂无明确呼吸困难。",
  "risk_level": "low",
  "red_flags": [],
  "department": "呼吸内科",
  "advice": "建议注意休息、补充水分；如发热持续不退、胸闷或呼吸困难，应及时线下就诊。",
  "references": []
}
```

## 推荐测试用例

低风险：

```json
{
  "user_input": "我发热两天了，还一直咳嗽"
}
```

高风险：

```json
{
  "user_input": "我胸痛，而且有点喘不上气"
}
```

信息不足：

```json
{
  "user_input": "我不舒服"
}
```

## 目录结构

```text
app/
├── api/              # FastAPI 路由层
├── core/             # 配置、Prompt、风险规则
├── service/          # 业务服务、LLM 服务、会话存储
├── schema/           # Pydantic 请求/响应模型
├── agent/            # 后续 LangGraph 工作流
├── tools/            # 后续 Tool Calling 工具
├── model/            # 后续数据库模型
└── utils/            # JSON 解析等工具函数
```

## 项目边界

这个项目不是：

- 医疗诊断系统
- 处方系统
- 医院 HIS/EMR 系统

这个项目是：

- 医疗问诊分诊 Agent Demo
- 一个偏工程展示和求职展示的项目

因此它的重点是主链路可运行、架构清晰、输出结构化、医疗安全边界明确。

## 后续计划

1. 扩充接口自动化测试和异常场景测试。
2. 将内存 `SessionStore` 替换为 Redis 或数据库。
3. 接入本地知识库检索，先做简单检索，再升级到 pgvector。
4. 用 LangGraph 重构问诊流程。
5. 接入 LangSmith 做调用链路观测。
