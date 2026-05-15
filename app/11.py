import requests
import json

# ================= 配置区域 =================
# 建议查完并调通后，立即去后台重置此密钥以保安全
API_KEY = "sk-Y6kxeZZ0NqcoRMvlaC6nc9aGJFhVeZsRAexiuBsxsDLN8cm5"
BASE_URL = "https://api.anyone.ai/v1/models"


# ===========================================

def get_anthropic_models():
    # 按照 Anyone 官方文档要求，构造 Anthropic 风格的请求头
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }

    try:
        print(f"正在以 Anthropic 模式请求模型列表...")
        response = requests.get(BASE_URL, headers=headers)

        if response.status_code == 200:
            data = response.json()
            print("\n✅ 获取成功！请从下方列表中复制模型 ID 到 CCSwitch：")
            print("-" * 60)

            # 兼容返回格式：可能是 {'data': [...]} 或直接是 [...]
            models = data.get('data', []) if isinstance(data, dict) else data

            if not models:
                print("列表为空，请检查中转站余额或权限。")
                return

            for m in models:
                mid = m.get('id')
                if mid:
                    # 重点关注包含 'sonnet' 的 ID
                    if "sonnet" in mid.lower():
                        print(f"👉 [推荐使用] {mid}")
                    else:
                        print(f"   [备选] {mid}")

            print("-" * 60)
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print(f"返回信息: {response.text}")

    except Exception as e:
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    get_anthropic_models()