const chatArea = document.getElementById("chat-area");
const form = document.getElementById("input-form");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const evaluateBtn = document.getElementById("evaluate-btn");
const resetBtn = document.getElementById("reset-btn");

let sessionId = null;
let canEvaluate = false;

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    addMessage("user", text);
    input.value = "";
    setLoading(true);

    try {
        let data;
        if (!sessionId) {
            data = await apiCall("POST", "/triage/start", { user_input: text });
            sessionId = data.session_id;
            evaluateBtn.disabled = false;
        } else {
            data = await apiCall("POST", "/triage/continue", {
                session_id: sessionId,
                user_input: text,
            });
            canEvaluate = !data.need_more_info;
        }

        renderTriageResponse(data);
    } catch (err) {
        addMessage("system", "请求失败：" + err.message);
    } finally {
        setLoading(false);
    }
});

evaluateBtn.addEventListener("click", async () => {
    if (!sessionId) return;
    setLoading(true);

    try {
        const data = await apiCall("POST", "/triage/evaluate", { session_id: sessionId });
        renderEvaluation(data);
        evaluateBtn.disabled = true;
        sendBtn.disabled = true;
        input.disabled = true;
    } catch (err) {
        addMessage("system", "评估请求失败：" + err.message);
    } finally {
        setLoading(false);
    }
});

resetBtn.addEventListener("click", () => {
    sessionId = null;
    canEvaluate = false;
    evaluateBtn.disabled = true;
    sendBtn.disabled = false;
    input.disabled = false;
    input.value = "";
    chatArea.innerHTML = `
        <div class="message system">
            <div class="bubble">
                你好，我是 AI 分诊助手。请描述你的症状，我会通过几个问题帮你评估情况并建议就诊科室。
            </div>
        </div>`;
});

function renderTriageResponse(data) {
    const riskClass = riskLabel(data.risk_level).class;
    const symptoms = data.symptoms || [];
    const missing = data.missing_fields || [];
    const redFlags = data.red_flags || [];

    let html = `<div>${escapeHtml(data.next_question || data.updated_summary || "")}</div>`;
    html += `<div class="meta">`;
    html += `<span>风险等级：<span class="${riskClass}">${data.risk_level}</span></span>`;
    if (symptoms.length) html += `<span>症状：${symptoms.map(escapeHtml).join("、")}</span>`;
    if (missing.length) html += `<span>待补充：${missing.map(escapeHtml).join("、")}</span>`;
    if (redFlags.length) html += `<span>红旗：${redFlags.map(escapeHtml).join("、")}</span>`;
    html += `</div>`;

    addMessage("system", html);
}

function renderEvaluation(data) {
    const risk = riskLabel(data.risk_level);

    let html = `<div class="result-card">`;
    html += `<h3>分诊建议</h3>`;
    html += `<div class="field"><strong>病情摘要：</strong>${escapeHtml(data.summary)}</div>`;
    html += `<div class="field"><strong>风险等级：</strong><span class="${risk.class}">${data.risk_level} ${risk.icon}</span></div>`;
    if (data.red_flags && data.red_flags.length) {
        html += `<div class="field"><strong>红旗症状：</strong>${data.red_flags.map(escapeHtml).join("、")}</div>`;
    }
    html += `<div class="field"><strong>建议科室：</strong>${escapeHtml(data.department)}</div>`;
    html += `<div class="field"><strong>医生建议：</strong>${escapeHtml(data.advice)}</div>`;
    if (data.references && data.references.length) {
        html += `<div class="field"><strong>参考来源：</strong><ul>`;
        data.references.forEach(ref => { html += `<li>${escapeHtml(ref)}</li>`; });
        html += `</ul></div>`;
    }
    html += `</div>`;

    addMessage("system", html);
}

function riskLabel(level) {
    const map = {
        "高": { icon: "🔴", class: "risk-high" },
        "中": { icon: "🟡", class: "risk-medium" },
        "低": { icon: "🟢", class: "risk-low" },
        "high": { icon: "🔴", class: "risk-high" },
        "medium": { icon: "🟡", class: "risk-medium" },
        "low": { icon: "🟢", class: "risk-low" },
    };
    return map[level] || { icon: "", class: "" };
}

function addMessage(role, content) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = content;
    div.appendChild(bubble);
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
}

async function apiCall(method, url, body) {
    const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

function setLoading(loading) {
    sendBtn.disabled = loading;
    if (loading) {
        const div = document.createElement("div");
        div.className = "message system";
        div.id = "loading-msg";
        div.innerHTML = '<div class="bubble"><span class="spinner"></span>思考中</div>';
        chatArea.appendChild(div);
        chatArea.scrollTop = chatArea.scrollHeight;
    } else {
        const el = document.getElementById("loading-msg");
        if (el) el.remove();
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}
