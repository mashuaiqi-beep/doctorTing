# doctorTing

doctorTing 是一个面向医疗问诊分诊场景的 Agent Demo，重点不在“替代医生诊断”，而在于展示一个相对完整的 LLM 应用工程雏形：

- FastAPI 后端接口
- 首轮问诊的 LangGraph 编排
- Redis 会话存储
- 规则 + LLM 的红旗症状识别
- 本地 Markdown 医学知识库 + ChromaDB RAG
- 简单可用的前端问诊工作台
- pytest 自动化测试

项目输出的是分诊建议和就医参考，不是诊断结论，也不能替代医生面诊。

## 当前状态

当前仓库已经从“能跑通的 API Demo”推进到“带前端、带检索、带会话状态的 Agent 雏形”：

- `POST /triage/start` 已切到 LangGraph 编排
- `POST /triage/continue` 和 `POST /triage/evaluate` 仍由 `TriageService` 负责主链路
- 会话存储当前默认使用 Redis
- 首页 `/` 已提供静态前端，可直接发起问诊和查看分诊结果
- `/triage/evaluate` 会接入知识检索结果并返回 `references`

## 已实现能力

### 1. 问诊接口

当前提供三条核心接口：

- `POST /triage/start`
- `POST /triage/continue`
- `POST /triage/evaluate`

接口模型定义在 [app/schema/triage_schema.py](/E:/py/doctorTing/app/schema/triage_schema.py)。

### 2. 首轮 LangGraph 编排

`start` 流程已经迁移到 [app/agent/triage_graph.py](/E:/py/doctorTing/app/agent/triage_graph.py)，当前节点顺序为：

1. LLM 抽取首轮问诊信息
2. 规则层风险判断
3. LLM 工具层风险判断
4. 合并风险结果
5. 写入 session
6. 组装响应

也就是说，LangGraph 现在已经接入真实业务链路，但只覆盖首轮问诊流程。

### 3. 风险控制

当前采用双层保守策略：

- 规则层：识别胸痛、呼吸困难等明确红旗词
- LLM 层：识别更口语化、语义化的高风险表达
- 合并策略：任一层命中高风险，最终结果即为高风险
- 高风险 session 在后续追问中不会被降级

相关实现位于：

- [app/core/risk_rules.py](/E:/py/doctorTing/app/core/risk_rules.py)
- [app/service/risk_control_service.py](/E:/py/doctorTing/app/service/risk_control_service.py)

### 4. RAG 检索

当前知识检索链路包括：

- 本地知识源：`data/knowledge/*.md`
- 向量服务：ChromaDB
- 索引构建脚本：[app/scripts/build_knowledge_index.py](/E:/py/doctorTing/app/scripts/build_knowledge_index.py)
- 最终输出：`evaluate` 阶段返回 `references`

目前既保留了公开工具入口，也保留了向量检索服务，方便后续做评估与扩展。

### 5. 前端页面

首页 `/` 已挂载静态页面，前端资源位于：

- [app/static/index.html](/E:/py/doctorTing/app/static/index.html)
- [app/static/styles.css](/E:/py/doctorTing/app/static/styles.css)
- [app/static/app.js](/E:/py/doctorTing/app/static/app.js)

这个页面已经能完成：

- 输入首轮症状
- 展示追问问题
- 展示风险等级、红旗症状、缺失字段
- 生成最终分诊建议

## 技术栈

- Python
- FastAPI
- Pydantic
- Redis
- OpenAI compatible SDK
- LangGraph
- ChromaDB
- pytest

## 目录结构

```text
app/
  api/         FastAPI 路由
  agent/       LangGraph 编排
  core/        配置、Prompt、风险规则
  model/       预留数据模型
  schema/      请求/响应模型
  service/     业务服务、LLM、Redis session、RAG 服务
  static/      前端页面
  tools/       工具函数与公开工具入口
  scripts/     索引构建脚本
  utils/       通用工具
data/
  knowledge/   Markdown 医学知识库
  chroma/      ChromaDB 持久化目录
docs/
  progress.md  当前进度记录
tests/
  接口、服务、工具、RAG 测试
```

## 启动方式

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

当前代码会读取这些环境变量：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
REDIS_URL=redis://:password@localhost:6379/0
REDIS_SESSION_TTL_SECONDS=86400
CHROMA_PERSIST_DIR=data/chroma
```

PowerShell 示例：

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
$env:OPENAI_BASE_URL="https://api.deepseek.com"
$env:OPENAI_MODEL="deepseek-chat"
$env:REDIS_URL="redis://:password@localhost:6379/0"
$env:REDIS_SESSION_TTL_SECONDS="86400"
$env:CHROMA_PERSIST_DIR="data/chroma"
```

### 3. 构建知识库索引

```bash
python -m app.scripts.build_knowledge_index
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload
```

启动后可访问：

- 首页：[http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Swagger：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 健康检查：[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

## 接口示例

### `POST /triage/start`

```json
{
  "user_input": "我发热两天了，还一直咳嗽"
}
```

返回结构：

```json
{
  "session_id": "xxx",
  "symptoms": ["发热", "咳嗽"],
  "missing_fields": ["最高体温", "是否呼吸困难"],
  "next_question": "请问最高体温是多少？有没有呼吸困难？",
  "risk_level": "low",
  "red_flags": []
}
```

### `POST /triage/continue`

```json
{
  "session_id": "xxx",
  "user_input": "最高 38.5 度，没有呼吸困难"
}
```

### `POST /triage/evaluate`

```json
{
  "session_id": "xxx"
}
```

返回结构包含：

- `summary`
- `risk_level`
- `red_flags`
- `department`
- `advice`
- `references`

## 测试

运行测试：

```bash
python -m pytest
```

当前测试覆盖重点包括：

- 三条问诊接口主流程
- 高风险识别
- 无效 `session_id` 的 404 返回
- 高风险 session 不降级
- 向量知识库构建与检索
- 工具层返回结构稳定性

## 当前待完善项

从当前代码状态看，下一阶段最值得继续推进的是：

1. 清理硬编码敏感配置，尤其是 [app/core/config.py](/E:/py/doctorTing/app/core/config.py) 里的默认密钥与 Redis 连接信息
2. 为 Redis 不可用场景补上更稳妥的降级策略或工厂切换
3. 把 `continue/evaluate` 也逐步纳入 LangGraph 编排
4. 建立 RAG 评估集，而不只是“能检索到结果”
5. 扩充知识库内容和疾病覆盖范围

## 项目边界

doctorTing 不是：

- 医疗诊断系统
- 处方系统
- 医院 HIS/EMR
- 可直接替代医生的线上医疗服务

doctorTing 更适合作为：

- LLM Agent 工程化 Demo
- 医疗场景安全边界设计 Demo
- RAG + 工具调用 + 会话管理的面试/展示项目
