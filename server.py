#!/usr/bin/env python3
"""
高报专家 Hermes Gateway - Render 部署版
提供 OpenAI 兼容接口，加载 SOUL.md 系统提示词
"""
from flask import Flask, request, Response, stream_with_context
import os
import json
import requests
from pathlib import Path

app = Flask(__name__)

# 配置
PORT = int(os.environ.get("PORT", 10000))
API_KEY = os.environ.get("API_KEY", "hermes-gateway-key")
SILICONFLOW_KEY = os.environ.get("SILICONFLOW_KEY", "")

# 加载 SOUL.md
SOUL_PATHS = [
    Path(__file__).parent / "SOUL.md",
    Path.home() / ".hermes-gaokao" / "SOUL.md"
]

def load_soul():
    """加载系统提示词"""
    for path in SOUL_PATHS:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "你是高考志愿填报专家助手。"

SOUL_PROMPT = load_soul()

@app.route('/health')
def health():
    """健康检查"""
    return {"status": "ok", "service": "hermes-gateway"}

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """OpenAI 兼容接口 - 转发到 SiliconFlow"""
    auth = request.headers.get("Authorization", "")
    if not auth or not auth.startswith("Bearer "):
        return {"error": "Missing Authorization"}, 401
    
    api_key = auth.replace("Bearer ", "")
    if api_key != API_KEY and not api_key.startswith("sk-"):
        return {"error": "Invalid API Key"}, 401
    
    # 解析请求
    data = request.json
    messages = data.get("messages", [])
    
    # 插入系统提示词（如果不存在）
    if not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": SOUL_PROMPT})
    
    # 转发到 SiliconFlow
    siliconflow_key = SILICONFLOW_KEY or api_key
    headers = {
        "Authorization": f"Bearer {siliconflow_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": data.get("model", "deepseek-ai/DeepSeek-V3"),
        "messages": messages,
        "stream": data.get("stream", False),
        "temperature": data.get("temperature", 0.7),
        "max_tokens": data.get("max_tokens", 2000)
    }
    
    stream = data.get("stream", False)
    
    if stream:
        def generate():
            with requests.post(
                "https://api.siliconflow.cn/v1/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=60
            ) as r:
                for line in r.iter_lines():
                    if line:
                        yield line + b"\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream'
        )
    else:
        resp = requests.post(
            "https://api.siliconflow.cn/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        return resp.json(), resp.status_code

if __name__ == '__main__':
    print(f"🚀 Hermes Gateway 启动在端口 {PORT}")
    print(f"📝 SOUL.md 已加载（{len(SOUL_PROMPT)} 字符）")
    app.run(host='0.0.0.0', port=PORT, debug=False)
