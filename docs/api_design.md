# API 设计

## 1. `POST /triage/start`

### Request

```json
{
  "user_input": "发热两天，咳嗽，胸口有点闷"
}
```

### Response

```json
{
  "session_id": "abc123",
  "symptoms": ["发热", "咳嗽", "胸闷"],
  "missing_fields": ["体温", "是否呼吸困难", "是否有基础病"],
  "next_question": "请问目前最高体温多少？有没有呼吸困难？",
  "risk_level": "high",
  "red_flags": ["胸闷"]
}
```

### 说明

职责：

- 创建新会话。
- 提取用户首轮症状。
- 判断缺失信息。
- 生成下一轮追问。
- 判断风险等级。

## 2. `POST /triage/continue`

### Request

```json
{
  "session_id": "abc123",
  "user_input": "最高 38.5 度，没有呼吸困难，有鼻塞"
}
```

### Response

```json
{
  "session_id": "abc123",
  "updated_summary": "发热 2 天，最高 38.5 度，伴咳嗽、胸闷、鼻塞，否认呼吸困难。",
  "next_question": "请问是否有基础病，是否正在服药？",
  "need_more_info": true
}
```

### 说明

职责：

- 读取已有会话。
- 追加用户回答。
- 更新症状、摘要、缺失信息和风险等级。
- 返回下一轮追问或结束判断。

无效 `session_id` 返回 `404`。

## 3. `POST /triage/evaluate`

### Request

```json
{
  "session_id": "abc123"
}
```

### Response

```json
{
  "summary": "发热 2 天，最高 38.5 度，伴咳嗽、胸闷、鼻塞，暂无明确呼吸困难。",
  "risk_level": "high",
  "red_flags": ["胸闷"],
  "department": "呼吸内科",
  "advice": "建议尽快线下就诊；如胸闷加重或出现呼吸困难，应立即前往急诊。",
  "references": []
}
```

### 说明

职责：

- 读取完整会话。
- 生成病情摘要。
- 返回最终风险等级和红旗症状。
- 推荐科室。
- 给出保守、安全的就医建议。

无效 `session_id` 返回 `404`。
