"""
LLM 代理路由 - /v1/chat/completions
支持多个免费 LLM 后端：Groq、SiliconFlow 等
注入高报专家 SOUL.md 系统提示词，支持 mobile 模式和 SSE 流式输出
支持 Function Calling（自动查询高考数据）
"""
import json
import os
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(tags=["LLM 代理"])

# ============================================================
# 配置检查端点（无需认证）
# ============================================================

@router.get("/v1/config")
async def get_config():
    """返回当前 LLM 配置（不包含 API Key）"""
    return {
        "llm_provider": LLM_PROVIDER,
        "llm_backend": LLM_BACKEND,
        "default_model": DEFAULT_MODEL,
        "description": current_config["description"],
        "api_key_configured": bool(LLM_API_KEY),
        "tools_count": len(TOOLS),
        "tools": [t["function"]["name"] for t in TOOLS]
    }

# ============================================================
# 多后端配置
# ============================================================

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "siliconflow")

# 各后端配置
LLM_CONFIGS = {
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
        "default_model": "glm-4-flash",
        "description": "智谱AI - GLM-4-Flash 永久免费"
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "llama-3.1-70b-versatile",
        "description": "Groq - 完全免费，Llama 3.1 70B"
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "LLM_API_KEY",
        "default_model": os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-72B-Instruct"),
        "description": "SiliconFlow - Qwen2.5-72B 支持 Function Calling"
    },
}

# 获取当前后端配置
current_config = LLM_CONFIGS.get(LLM_PROVIDER, LLM_CONFIGS["groq"])
LLM_BACKEND = os.environ.get("LLM_BACKEND", current_config["base_url"])
LLM_API_KEY = os.environ.get(current_config["api_key_env"], "")
DEFAULT_MODEL = current_config["default_model"]

print(f"🤖 LLM 后端: {LLM_PROVIDER} ({current_config['description']})")
print(f"🔍 调试信息:")
print(f"   LLM_PROVIDER = {LLM_PROVIDER}")
print(f"   LLM_BACKEND = {LLM_BACKEND}")
print(f"   API Key Env = {current_config['api_key_env']}")
print(f"   API Key 已配置 = {bool(LLM_API_KEY)}")
print(f"   DEFAULT_MODEL = {DEFAULT_MODEL}")

# 高报专家 V2.0 SOUL.md（内嵌，避免 Render 上读本地文件）
SOUL_PROMPT = """你是「高报专家」，一个专业、温暖、有洞察力的高考志愿填报AI顾问。

核心方法论：
1. 摆渡人哲学 - 追问而非给答案，真诚第一，长期主义
2. YAI苏格拉底式追问 - 由浅入深、由宽到窄、由外在到内在、由现在到未来
3. 家庭背景分流 - 按经济条件/父母职业/人脉资源/试错空间分策略
4. 就业倒推法 - 从中位数毕业生去向倒推专业选择，关注AI替代风险
5. 人生3.0框架 - 别人安排→追求成功→自我实现
6. OKR人生规划 - 人生目标→大学/专业支撑→能力培养

对话原则：
- 先问后答，不急着给学校推荐
- 苏格拉底式引导，用提问代替说教
- 数据驱动，引用具体分数线和位次
- 不确定的数据标注"需核实"，不做绝对承诺

【重要】当用户询问以下内容时，必须使用提供的工具查询真实数据：
- 搜索院校 → 使用 search_colleges 工具
- 查询院校录取分数 → 使用 get_college_scores 工具
- 查询省控线 → 使用 get_province_control_line 工具
不要仅凭记忆回答，必须使用工具获取最新数据。"""

MOBILE_INSTRUCTION = """

═══════════════════════════════════════
【最高优先级 · 不可违反】当前模式: mode=mobile
你正在与手机端的普通用户（学生/家长）直接聊天。
═══════════════════════════════════════

硬性规则（违反任何一条=输出不合格）：
1. 单条回复严格不超过 100 字。超过就是失败。
2. 每次只说一件事：问1个问题，或给1个建议。
3. 不用 emoji 标记符号（📋💡⚠️❌✅1️⃣→ 全部禁止）
4. 不用编号列表，不用箭头，不用表格
5. 像微信朋友聊天一样说话，不要像写报告
6. 直接叫"你"，不要叫"考生""学生"
7. 如果需要对方选择，末尾写：【选项】A / B / C

示例正确输出：
"580分想学计算机，这个分数不错 👍 
你在哪个省？不同省份情况差挺多的。
【选项】河南 / 山东 / 四川"

示例错误输出：
"📋 已识别信息：
1️⃣ 分数：580 → ❌ 这是专家模式格式，手机端禁止！"
"""


# ============================================================
# Function Calling 工具定义
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_colleges",
            "description": "搜索院校信息（按省份、类型、批次等筛选）",
            "parameters": {
                "type": "object",
                "properties": {
                    "province": {"type": "string", "description": "省份名称，如'陕西'、'北京'"},
                    "college_type": {"type": "string", "description": "院校类型：'985'、'211'、'双一流'、'普通本科'、'高职高专'"},
                    "keyword": {"type": "string", "description": "院校名称关键词，如'交通'、'师范'"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_college_scores",
            "description": "查询具体院校的历年录取分数线",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_name": {"type": "string", "description": "院校全称，如'清华大学'"},
                    "province": {"type": "string", "description": "生源地省份"},
                    "year": {"type": "integer", "description": "年份：2022、2023、2024"}
                },
                "required": ["college_name", "province"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_province_control_line",
            "description": "查询某省某批次的控制分数线（省控线）",
            "parameters": {
                "type": "object",
                "properties": {
                    "province": {"type": "string", "description": "省份名称"},
                    "batch": {"type": "string", "description": "批次：'本科一批'、'本科二批'、'专科批'"},
                    "category": {"type": "string", "description": "科类：'文科'、'理科'、'物理类'、'历史类'、'综合'"},
                    "year": {"type": "integer", "description": "年份：2022、2023、2024"}
                },
                "required": ["province", "batch", "category"]
            }
        }
    }
]


# ============================================================
# 工具执行函数（TODO：连接真实数据库）
# ============================================================

async def execute_tool(tool_name: str, tool_args: Dict[str, Any], db_session) -> str:
    """执行工具调用，返回结果字符串"""
    print(f"🔧 执行工具: {tool_name} | 参数: {tool_args}")
    
    try:
        if tool_name == "search_colleges":
            # TODO: 实际查询数据库
            province = tool_args.get("province", "")
            college_type = tool_args.get("college_type", "")
            keyword = tool_args.get("keyword", "")
            
            # 模拟数据（实际应该从数据库查询）
            return json.dumps({
                "status": "success",
                "data": [
                    {"name": f"{province}大学（示例）", "province": province, "type": college_type or "普通本科"},
                    {"name": f"{keyword or '理工'}大学（示例）", "province": province, "type": college_type or "普通本科"}
                ],
                "message": "⚠️ 当前为模拟数据，需要连接真实数据库"
            }, ensure_ascii=False)
            
        elif tool_name == "get_college_scores":
            college_name = tool_args.get("college_name", "")
            province = tool_args.get("province", "")
            year = tool_args.get("year", 2024)
            
            return json.dumps({
                "status": "success",
                "college": college_name,
                "province": province,
                "year": year,
                "scores": [
                    {"major": "计算机科学", "min_score": 580, "avg_score": 590},
                    {"major": "电子信息", "min_score": 575, "avg_score": 585}
                ],
                "message": "⚠️ 当前为模拟数据，需要连接真实数据库"
            }, ensure_ascii=False)
            
        elif tool_name == "get_province_control_line":
            province = tool_args.get("province", "")
            batch = tool_args.get("batch", "")
            category = tool_args.get("category", "")
            year = tool_args.get("year", 2024)
            
            return json.dumps({
                "status": "success",
                "province": province,
                "batch": batch,
                "category": category,
                "year": year,
                "control_line": 450,
                "message": "⚠️ 当前为模拟数据，需要连接真实数据库"
            }, ensure_ascii=False)
        
        else:
            return json.dumps({
                "status": "error",
                "message": f"未知工具: {tool_name}"
            }, ensure_ascii=False)
    
    except Exception as e:
        print(f"❌ 工具执行失败: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)


# ============================================================
# 请求模型
# ============================================================

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    stream: Optional[bool] = True
    temperature: Optional[float] = 0.7
    tools: Optional[List[Dict]] = None  # 支持前端传入自定义工具


# ============================================================
# 路由
# ============================================================

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, request_obj: Request):
    """OpenAI 兼容的 chat completions 代理接口（支持 Function Calling）"""
    
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="LLM_API_KEY 未配置，请设置环境变量"
        )
    
    # 获取数据库 session（用于工具执行）
    from db import SessionLocal
    db = SessionLocal()
    
    try:
        # 构造带系统提示词的的数据列表
        system_content = SOUL_PROMPT + MOBILE_INSTRUCTION
        injected_messages = [
            {"role": "system", "content": system_content},
        ] + [m.model_dump() for m in request.messages]
        
        # 使用请求中的 tools，或默认注入 TOOLS
        tools = request.tools if request.tools else TOOLS
        
        # 构造转发给 LLM 后端的请求体（第一步：非流式，检查是否有工具调用）
        payload_step1 = {
            "model": request.model or DEFAULT_MODEL,
            "messages": injected_messages,
            "tools": tools,
            "tool_choice": "auto",  # 明确允许模型选择是否调用工具
            "stream": False,  # 第一步必须非流式
            "temperature": request.temperature or 0.7,
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        }
        
        user_msg = request.messages[-1].content[:50] if request.messages else "(空)"
        print(f"📡 LLM代理请求(Step 1): model={payload_step1['model']} | 用户: {user_msg}...")
        print(f"📡 工具数量: {len(tools)} | 工具列表: {[t['function']['name'] for t in tools]}")
        
        async with httpx.AsyncClient(timeout=120) as client:
            # === 第一步：发送请求，检查是否有工具调用 ===
            resp1 = await client.post(
                f"{LLM_BACKEND}/chat/completions",
                json=payload_step1,
                headers=headers,
            )
            
            if resp1.status_code != 200:
                raise HTTPException(
                    status_code=resp1.status_code,
                    detail=f"LLM 后端错误: {resp1.text[:500]}"
                )
            
            resp1_data = resp1.json()
            
            # 检查是否有工具调用
            choice = resp1_data["choices"][0]
            message = choice["message"]
            
            if "tool_calls" in message and message["tool_calls"]:
                # === 有工具调用，执行工具 ===
                tool_calls = message["tool_calls"]
                print(f"🔧 检测到 {len(tool_calls)} 个工具调用")
                
                # 执行所有工具调用
                tool_results = []
                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    tool_args = json.loads(tc["function"]["arguments"])
                    
                    result = await execute_tool(tool_name, tool_args, db)
                    tool_results.append({
                        "tool_call_id": tc["id"],
                        "role": "tool",
                        "name": tool_name,
                        "content": result
                    })
                
                # 构造第二步的消息列表（包含工具调用结果）
                messages_step2 = injected_messages + [
                    {
                        "role": "assistant",
                        "content": message.get("content", ""),
                        "tool_calls": tool_calls
                    }
                ] + tool_results
                
                # 第二步：请求最终回复（支持流式）
                payload_step2 = {
                    "model": request.model or DEFAULT_MODEL,
                    "messages": messages_step2,
                    "stream": request.stream if request.stream is not None else True,
                    "temperature": request.temperature or 0.7,
                }
                
                print(f"📡 LLM代理请求(Step 2): 发送工具结果，请求最终回复...")
                
                resp2 = await client.post(
                    f"{LLM_BACKEND}/chat/completions",
                    json=payload_step2,
                    headers={**headers, "Accept": "text/event-stream"},
                )
                
                if resp2.status_code != 200:
                    raise HTTPException(
                        status_code=resp2.status_code,
                        detail=f"LLM 后端错误(Step 2): {resp2.text[:500]}"
                    )
                
                # 处理第二步的响应（流式或非流式）
                if payload_step2["stream"]:
                    # === 流式响应 ===
                    async def event_stream():
                        async for line in resp2.aiter_lines():
                            if line.startswith("data: ") and line != "data: [DONE]":
                                json_str = line[6:]
                                try:
                                    json.loads(json_str)  # 验证 JSON 合法性
                                    yield f"{line}\n\n"
                                except json.JSONDecodeError:
                                    pass
                            elif line == "data: [DONE]":
                                yield "data: [DONE]\n\n"
                    
                    return StreamingResponse(
                        event_stream(),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "Access-Control-Allow-Origin": "*",
                        }
                    )
                else:
                    # === 非流式响应 ===
                    return JSONResponse(
                        content=resp2.json(),
                        headers={"Access-Control-Allow-Origin": "*"}
                    )
            else:
                # === 没有工具调用，直接返回第一步的响应 ===
                print("✅ 无工具调用，直接返回")
                
                if request.stream is not None and request.stream == False:
                    # 非流式，直接返回
                    return JSONResponse(
                        content=resp1_data,
                        headers={"Access-Control-Allow-Origin": "*"}
                    )
                else:
                    # 流式，需要重新请求（因为第一步用了 stream=False）
                    payload_stream = {
                        **payload_step1,
                        "stream": True
                    }
                    
                    resp_stream = await client.post(
                        f"{LLM_BACKEND}/chat/completions",
                        json=payload_stream,
                        headers={**headers, "Accept": "text/event-stream"},
                    )
                    
                    async def event_stream():
                        async for line in resp_stream.aiter_lines():
                            if line.startswith("data: ") and line != "data: [DONE]":
                                json_str = line[6:]
                                try:
                                    json.loads(json_str)
                                    yield f"{line}\n\n"
                                except json.JSONDecodeError:
                                    pass
                            elif line == "data: [DONE]":
                                yield "data: [DONE]\n\n"
                    
                    return StreamingResponse(
                        event_stream(),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "Access-Control-Allow-Origin": "*",
                        }
                    )
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"无法连接 LLM 服务: {e}")
    
    finally:
        db.close()
