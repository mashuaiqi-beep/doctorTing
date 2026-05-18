# doctorTing - Medical Triage Agent

doctorTing 是一个面向 Agent 实习、求职和项目展示的医疗问诊分诊 Demo。

项目目标不是替代医生诊断，也不是完整医院系统，而是用一个可运行的后端服务展示：

- 多轮问诊
- 红旗症状识别
- 结构化 JSON 输出
- 会话状态管理
- ToolService 工具层
- 本地医学知识库检索
- ChromaDB 向量 RAG
- 模拟科室推荐
- 自动化测试

## 项目边界

doctorTing 不是：

- 医疗诊断系统
- 处方系统
- 医院 HIS/EMR 系统
- 可以替代医生的线上医疗服务

doctorTing 是：

- 医疗问诊分诊 Agent Demo
- 一个用于展示后端工程、LLM 应用、RAG 和医疗安全边界意识的项目

因此项目中的建议都应理解为分诊和就医建议，不是诊断结论。

## 当前进度

当前项目处于：

```text
Agent MVP 增强阶段：三条核心问诊接口已跑通，ToolService 和 ChromaDB RAG 已接入，正在向 LangGraph 编排、Redis 会话和评估体系演进。
```

已经完成：

- `POST /triage/start`：开始问诊，抽取症状、缺失信息、下一轮追问，并判断风险。
- `POST /triage/continue`：基于 `session_id` 继续问诊，更新摘要、症状、缺失信息和风险状态。
- `POST /triage/evaluate`：基于完整 session 生成最终分诊建议。
- 规则 + LLM 双层红旗症状识别。
- 高风险保守合并策略。
- 高风险 session 后续不降级。
- 内存版 `SessionStore`。
- Redis 版 `RedisSessionStore` 雏形。
- `ToolService` 工具层。
- 本地 Markdown 医疗知识库。
- ChromaDB 向量知识库服务。
- `/triage/evaluate` 阶段接入知识检索和 references 返回。
- 模拟挂号/科室推荐工具。
- pytest 覆盖接口、service、tools 和 RAG。

仍在规划或待完善：

- LangGraph 主链路编排。
- Redis session 工厂和配置切换。
- 数据库长期问诊记录。
- LangSmith 可观测。
- RAG 评估集和批量评估脚本。
- 更完整的医学知识库。

## 技术栈

- 后端：`Python`、`FastAPI`
- 数据模型：`Pydantic`
- LLM：OpenAI SDK 兼容接口
- Prompt：集中在 `app/core/prompt_manager.py`
- 风险控制：关键词规则 + LLM/Tool Calling 语义识别
- 会话：内存版 `SessionStore`，预留 Redis 版 `RedisSessionStore`
- 工具层：`ToolService`
- RAG：Markdown 知识库 + ChromaDB
- Embedding：`shibing624/text2vec-base-chinese`
- 测试：`pytest`、`fastapi.testclient`
- 后续编排：`LangGraph`

## 主流程

```text
用户输入症状
  -> /triage/start
  -> LLM 抽取症状、缺失字段、下一轮追问
  -> 规则 + LLM 检查红旗症状
  -> 创建 session
  -> /triage/continue
  -> 基于 session 更新问诊状态
  -> /triage/evaluate
  -> ChromaDB 检索医学知识库
  -> 模拟挂号工具推荐科室
  -> LLM 结合问诊记录和知识库生成分诊建议
  -> 返回结构化 JSON
```

## 风险控制设计

医疗分诊场景不能完全依赖 LLM，所以项目采用双层风险识别：

```text
规则关键词匹配
  +
LLM / Tool Calling 语义判断
  ->
保守合并
```

规则层负责识别明确红旗词，例如：

- 胸痛
- 胸闷
- 呼吸困难
- 喘不上气
- 意识模糊
- 抽搐
- 高热不退
- 昏迷
- 便血
- 呕血
- 咯血
- 严重头痛
- 剧烈腹痛
- 持续加重

LLM 层负责识别口语化表达，例如：

- 胸口像被压着
- 喘不过来
- 人有点迷糊

合并策略：

- 规则命中高风险，则最终 `risk_level=high`。
- LLM 判断高风险，则最终 `risk_level=high`。
- LLM 调用失败时，回退到规则判断。
- 如果 session 已经是高风险，后续问诊不会把风险降级。

## RAG 设计

当前 RAG 主链路使用：

```text
data/knowledge/*.md
  -> Markdown 段落切 chunk
  -> ChromaDB 持久化 collection
  -> evaluate 阶段按症状 query 检索 top_k
  -> 检索结果注入 Prompt
  -> 响应返回 references
```

知识库目录：

```text
data/knowledge/
  fever.md
  cough.md
  chest_pain.md
```

重建向量索引：

```bash
python -m app.scripts.build_knowledge_index
```

## 启动方式

安装依赖：

```bash
pip install -r requirements.txt
```

配置环境变量：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
CHROMA_PERSIST_DIR=data/chroma
```

PowerShell 临时配置示例：

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
$env:OPENAI_BASE_URL="https://api.deepseek.com"
$env:OPENAI_MODEL="deepseek-chat"
$env:CHROMA_PERSIST_DIR="data/chroma"
```

启动服务：

```bash
uvicorn app.main:app --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

健康检查：

```text
http://127.0.0.1:8000/health
```

运行测试：

```bash
python -m pytest
```

## 接口说明

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

无效 `session_id` 返回 404。

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
  "references": ["fever.md", "cough.md"]
}
```

无效 `session_id` 返回 404。

## 推荐 Demo 输入

低风险：

```json
{
  "user_input": "我发热两天了，还一直咳嗽"
}
```

高风险：

```json
{
  "user_input": "我胸口像被压着，而且有点喘不上气"
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
├── api/                  # FastAPI 路由层
├── core/                 # 配置、Prompt、风险规则
├── service/              # 业务服务、LLM 服务、工具服务、会话存储、向量知识库
├── schema/               # Pydantic 请求/响应模型
├── agent/                # LangGraph 工作流预留
├── tools/                # 可复用工具函数
├── model/                # 数据库模型预留
├── scripts/              # 知识库索引构建脚本
└── utils/                # JSON 解析等工具函数

data/
├── knowledge/            # Markdown 医疗知识库
└── chroma/               # ChromaDB 本地持久化数据

tests/                    # 自动化测试
docs/                     # 项目设计、进度和路线图
```

## 测试覆盖

当前测试包括：

- 三条接口完整流程。
- 高风险输入识别。
- 无效 `session_id` 返回 404。
- LLM 判断失败时规则仍能兜底。
- 高风险 session 后续不降级。
- 模拟挂号工具。
- 本地知识检索工具。
- ChromaDB 向量索引构建和检索。

运行：

```bash
python -m pytest
```

## 当前待办

优先级较高：

1. 清理配置中的默认密钥，改为完全从环境变量读取。
2. 增加 `.env.example`。
3. 增加 session store 工厂，支持 `memory` / `redis` 配置切换。
4. 扩充知识库文档。
5. 建立 RAG 评估集，评估 recall@k、references 命中率和建议质量。

中期目标：

1. 用 LangGraph 重构问诊流程。
2. 高风险输入走急诊建议分支。
3. 接入 LangSmith 做链路观测。
4. 保存最终问诊记录到数据库。
5. 增加更多异常场景和回归测试。

## 面试表达

可以这样概括项目：

> doctorTing 是一个医疗问诊分诊 Agent Demo。我用 FastAPI 提供 start、continue、evaluate 三条接口，通过 session 维护多轮问诊上下文；用 LLM 做症状抽取和建议生成，用规则加 LLM 做红旗症状识别；用 ToolService 封装知识检索和科室推荐；用 ChromaDB 检索本地 Markdown 医疗知识库，并在最终建议中返回 references。项目重点不是替代医生，而是展示 LLM 应用工程化、RAG、工具调用雏形和医疗安全边界设计。
