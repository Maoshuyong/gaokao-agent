"""
LLM 代理路由 - /v1/chat/completions
支持多个免费 LLM 后端：Groq、SiliconFlow 等
注入高报专家 SOUL.md 系统提示词，支持 mobile 模式和 SSE 流式输出
支持后端意图解析（自动查询高考数据，不依赖 LLM Function Calling）
"""
import json
import os
import re
import sqlite3
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
        "default_model": os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen3.5-35B-A3B"),
        "description": "SiliconFlow - Qwen3.5 支持 Function Calling"
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

【重要】当用户询问以下内容时，会自动调用工具查询数据：
- 搜索院校 → search_colleges 工具
- 查询院校录取分数 → get_college_scores 工具
- 查询省控线 → get_province_control_line 工具
- 查询专业招生数据 → search_major_enrollments 工具

【数据处理原则】
- 如果工具返回的数据包含"模拟数据"提示，说明当前是测试环境，你可以结合自己的知识给出准确回答
- 如果工具返回了真实数据，必须优先使用工具数据
- 不确定的数据标注"需核实"，不做绝对承诺"""

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
# Function Calling 工具定义（保留，用于文档和前端）
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_major_enrollments",
            "description": "查询专业级招生数据（包含院校、专业、历年录取分数、招生计划），当用户询问某院校有哪些专业、某专业的录取分数或招生计划时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_name": {"type": "string", "description": "院校名称关键词，如'清华大学'"},
                    "major_name": {"type": "string", "description": "专业名称关键词，如'计算机'"},
                    "province": {"type": "string", "description": "省份名称，如'陕西'"},
                    "year": {"type": "integer", "description": "年份：2022、2023、2024、2025"}
                }
            }
        }
    }
]


# ============================================================
# 后端意图解析（SiliconFlow Function Calling 不靠谱，自己解析）
# ============================================================

def detect_intent(user_message: str) -> tuple:
    """
    检测用户意图，返回 (tool_name, tool_args) 或 (None, None)
    关键词匹配规则（简单但有效）
    """
    msg = user_message.lower()
    
    # 省份列表（用于提取）
    provinces = ["北京", "上海", "天津", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
                 "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
                 "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海",
                 "内蒙古", "广西", "西藏", "宁夏", "新疆"]
    
    # 1. 检测 search_colleges（搜索院校）
    # 关键词：大学、学院、985、211、双一流、高校
    college_keywords = ["大学", "学院", "985", "211", "双一流", "高校", "本科学校"]
    if any(kw in msg for kw in college_keywords) and "专业" not in msg:
        args = {}
        
        # 提取省份
        for prov in provinces:
            if prov in msg:
                args["province"] = prov
                break
        
        # 提取院校类型
        if "985" in msg:
            args["college_type"] = "985"
        elif "211" in msg:
            args["college_type"] = "211"
        elif "双一流" in msg:
            args["college_type"] = "双一流"
        
        # 提取关键词（如"交通"、"师范"）
        kw_match = re.search(r'([\u4e00-\u9fa5]{2,4})(大学|学院)', msg)
        if kw_match:
            args["keyword"] = kw_match.group(1)
        
        return ("search_colleges", args)
    
    # 2. 检测 get_college_scores（查询录取分数）
    # 关键词：分数、录取、分数线、多少分
    score_keywords = ["分数", "录取", "分数线", "多少分", "投档"]
    if any(kw in msg for kw in score_keywords) and "专业" not in msg:
        args = {}
        
        # 提取院校名称（简单匹配：XXX大学/学院）
        college_match = re.search(r'([\u4e00-\u9fa5]{2,10})(大学|学院)', msg)
        if college_match:
            args["college_name"] = college_match.group(0)
        
        # 提取省份
        for prov in provinces:
            if prov in msg:
                args["province"] = prov
                break
        
        # 提取年份
        year_match = re.search(r'20(\d{2})', msg)
        if year_match:
            args["year"] = int("20" + year_match.group(1))
            
        if "college_name" in args and "province" in args:
            return ("get_college_scores", args)
    
    # 3. 检测 get_province_control_line（查询省控线）
    # 关键词：省控线、批次线、本科线、专科线
    control_keywords = ["省控线", "批次线", "本科线", "专科线", "控制线"]
    if any(kw in msg for kw in control_keywords):
        args = {}
        
        # 提取省份
        for prov in provinces:
            if prov in msg:
                args["province"] = prov
                break
        
        # 提取批次
        if "一批" in msg or "本科一批" in msg:
            args["batch"] = "本科一批"
        elif "二批" in msg or "本科二批" in msg:
            args["batch"] = "本科二批"
        elif "专科" in msg:
            args["batch"] = "专科批"
            
        # 提取科类
        if "文科" in msg or "历史" in msg:
            args["category"] = "文科"
        elif "理科" in msg or "物理" in msg:
            args["category"] = "理科"
        elif "综合" in msg:
            args["category"] = "综合"
            
        # 提取年份
        year_match = re.search(r'20(\d{2})', msg)
        if year_match:
            args["year"] = int("20" + year_match.group(1))
            
        if "province" in args and "batch" in args and "category" in args:
            return ("get_province_control_line", args)
    
    # 4. 检测 search_major_enrollments（查询专业招生数据）
    # 关键词：专业、招生、计划
    major_keywords = ["专业", "招生", "计划", "录取专业"]
    if any(kw in msg for kw in major_keywords):
        args = {}

        # 提取院校名称
        college_match = re.search(r'([\u4e00-\u9fa5]{2,10})(大学|学院)', msg)
        if college_match:
            args["college_name"] = college_match.group(0)

        # 提取专业名称（"XX专业"模式，排除大学/学院名称）
        # 只匹配2-6个汉字+专业，且不含"大学""学院"
        major_match = re.search(r'(?!.*(大学|学院))([\u4e00-\u9fa5]{2,6})专业', msg)
        if major_match:
            candidate = major_match.group(2)
            if "大学" not in candidate and "学院" not in candidate:
                args["major_name"] = candidate

        # 提取省份
        for prov in provinces:
            if prov in msg:
                args["province"] = prov
                break

        # 提取年份
        year_match = re.search(r'20(\d{2})', msg)
        if year_match:
            args["year"] = int("20" + year_match.group(1))

        # 如果有足够的条件，返回意图
        if "college_name" in args or "major_name" in args:
            return ("search_major_enrollments", args)

    # 无匹配意图
    return (None, None)


# ============================================================
# 工具执行函数（已连接真实数据库）
# ============================================================

async def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """执行工具调用，查询真实数据库，返回结果字符串"""
    print(f"🔧 执行工具: {tool_name} | 参数: {tool_args}")
    
    # 连接数据库（优先使用环境变量，否则使用示例数据库）
    db_path = os.environ.get("DATABASE_PATH", 
                        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gaokao_shanxi_recruit.db"))
    print(f"📂 数据库路径: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
    cursor = conn.cursor()
    
    try:
        if tool_name == "search_colleges":
            # 查询院校信息
            province = tool_args.get("province", "")
            college_type = tool_args.get("college_type", "")
            keyword = tool_args.get("keyword", "")
            
            # 构造查询
            query = "SELECT id, name, province, city, level, type, is_985, is_211, is_double_first FROM colleges WHERE 1=1"
            params = []
            
            if province:
                query += " AND province = ?"
                params.append(province)
            if college_type == "985":
                query += " AND is_985 = 1"
            elif college_type == "211":
                query += " AND is_211 = 1"
            elif college_type == "双一流":
                query += " AND is_double_first = 1"
            if keyword:
                query += " AND (name LIKE ? OR short_name LIKE ?)"
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            query += " LIMIT 20"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "name": row["name"],
                    "province": row["province"],
                    "city": row["city"],
                    "level": row["level"],
                    "type": row["type"],
                    "is_985": bool(row["is_985"]),
                    "is_211": bool(row["is_211"]),
                    "is_double_first": bool(row["is_double_first"])
                })
            
            return json.dumps({
                "status": "success",
                "data": results,
                "total": len(results)
            }, ensure_ascii=False)
            
        elif tool_name == "get_college_scores":
            # 查询院校录取分数
            college_name = tool_args.get("college_name", "")
            province = tool_args.get("province", "")
            year = tool_args.get("year", 2024)
            
            query = """
                SELECT college_name, year, province, batch, category, 
                       min_score, min_rank, avg_score, control_score
                FROM scores 
                WHERE college_name LIKE ? AND province = ? AND year = ?
                ORDER BY year DESC, batch, category
            """
            cursor.execute(query, (f"%{college_name}%", province, year))
            rows = cursor.fetchall()
            
            if not rows:
                return json.dumps({
                    "status": "error",
                    "message": f"未找到 {college_name} 在 {province} {year}年的录取数据"
                }, ensure_ascii=False)
            
            scores = []
            for row in rows:
                scores.append({
                    "year": row["year"],
                    "province": row["province"],
                    "batch": row["batch"],
                    "category": row["category"],
                    "min_score": row["min_score"],
                    "min_rank": row["min_rank"],
                    "avg_score": row["avg_score"],
                    "control_score": row["control_score"]
                })
            
            return json.dumps({
                "status": "success",
                "college": college_name,
                "province": province,
                "year": year,
                "scores": scores
            }, ensure_ascii=False)
            
        elif tool_name == "get_province_control_line":
            # 查询省控线（从scores表中获取control_score）
            province = tool_args.get("province", "")
            batch = tool_args.get("batch", "")
            category = tool_args.get("category", "")
            year = tool_args.get("year", 2024)
            
            query = """
                SELECT province, year, batch, category, control_score, MIN(min_score) as min_control
                FROM scores 
                WHERE province = ? AND batch = ? AND category = ? AND year = ?
                GROUP BY province, year, batch, category
                LIMIT 1
            """
            cursor.execute(query, (province, batch, category, year))
            row = cursor.fetchone()
            
            if not row:
                return json.dumps({
                    "status": "error",
                    "message": f"未找到 {province} {year}年 {batch} {category} 的省控线数据"
                }, ensure_ascii=False)
            
            control_line = row["control_score"] if row["control_score"] else row["min_control"]
            
            return json.dumps({
                "status": "success",
                "province": row["province"],
                "year": row["year"],
                "batch": row["batch"],
                "category": row["category"],
                "control_line": control_line
            }, ensure_ascii=False)
        
        elif tool_name == "search_major_enrollments":
            # 查询专业级招生数据
            college_name = tool_args.get("college_name", "")
            major_name = tool_args.get("major_name", "")
            province = tool_args.get("province", "")
            year = tool_args.get("year", 2025)

            # 构造查询
            query = """
                SELECT id, college_name, major_name, year, province, batch, category,
                       plan_count, enrollment_2024, enrollment_2023, enrollment_2022,
                       score_2024_min, rank_2024_min, score_2023_min, rank_2023_min,
                       duration, tuition, college_rank, double_first_class
                FROM major_enrollments
                WHERE 1=1
            """
            params = []

            if college_name:
                query += " AND college_name LIKE ?"
                params.append(f"%{college_name}%")
            if major_name:
                query += " AND major_name LIKE ?"
                params.append(f"%{major_name}%")
            if province:
                query += " AND province = ?"
                params.append(province)
            if year:
                query += " AND year = ?"
                params.append(year)

            query += " LIMIT 20"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "college_name": row["college_name"],
                    "major_name": row["major_name"],
                    "year": row["year"],
                    "province": row["province"],
                    "batch": row["batch"],
                    "category": row["category"],
                    "plan_count": row["plan_count"],
                    "enrollment_2024": row["enrollment_2024"],
                    "enrollment_2023": row["enrollment_2023"],
                    "enrollment_2022": row["enrollment_2022"],
                    "score_2024_min": row["score_2024_min"],
                    "rank_2024_min": row["rank_2024_min"],
                    "score_2023_min": row["score_2023_min"],
                    "rank_2023_min": row["rank_2023_min"],
                    "duration": row["duration"],
                    "tuition": row["tuition"],
                    "college_rank": row["college_rank"],
                    "double_first_class": bool(row["double_first_class"]) if row["double_first_class"] is not None else None
                })

            return json.dumps({
                "status": "success",
                "data": results,
                "total": len(results),
                "query": {
                    "college_name": college_name,
                    "major_name": major_name,
                    "province": province,
                    "year": year
                }
            }, ensure_ascii=False)

        else:
            return json.dumps({
                "status": "error",
                "message": f"未知工具: {tool_name}"
            }, ensure_ascii=False)
    
    except Exception as e:
        print(f"❌ 工具执行失败: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)
    
    finally:
        conn.close()


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
    tools: Optional[List[Dict]] = None  # 保留，用于前端自定义


# ============================================================
# 路由（后端意图解析版本）
# ============================================================

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, request_obj: Request):
    """OpenAI 兼容的 chat completions 代理接口（后端意图解析）"""
    
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="LLM_API_KEY 未配置，请设置环境变量"
        )
    
    try:
        # 获取用户最新消息
        user_message = request.messages[-1].content if request.messages else ""
        
        # === 后端意图解析（不依赖 LLM Function Calling）===
        tool_name, tool_args = detect_intent(user_message)
        
        # 构造系统提示词（基础版）
        system_content = SOUL_PROMPT + MOBILE_INSTRUCTION
        
        # 如果有意图匹配，调用工具并将结果注入到系统提示词
        if tool_name and tool_args:
            print(f"🎯 后端意图解析：检测到 {tool_name} | 参数：{tool_args}")
            tool_result = await execute_tool(tool_name, tool_args)
            
            # 将工具结果注入到系统提示词
            tool_context = f"""

═══════════════════════════════════════
【高考数据查询结果】
你刚刚调用了 {tool_name} 工具，结果如下：

{tool_result}

请基于以上真实数据回答用户问题。不要说"工具返回"，直接说数据内容。
═══════════════════════════════════════
"""
            system_content += tool_context
            print(f"✅ 工具结果已注入到系统提示词")
        
        # 构造消息列表（包含增强的系统提示词）
        injected_messages = [
            {"role": "system", "content": system_content},
        ] + [m.model_dump() for m in request.messages]
        
        # 不再使用 tools 参数（SiliconFlow Function Calling 不靠谱）
        print(f"📡 LLM代理请求: model={request.model or DEFAULT_MODEL} | 用户: {user_message[:50]}...")
        
        # 构造请求体（不包含 tools）
        payload = {
            "model": request.model or DEFAULT_MODEL,
            "messages": injected_messages,
            "stream": request.stream if request.stream is not None else True,
            "temperature": request.temperature or 0.7,
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        }
        
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{LLM_BACKEND}/chat/completions",
                json=payload,
                headers={**headers, "Accept": "text/event-stream"},
            )
            
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"LLM 后端错误: {resp.text[:500]}"
                )
            
            # 处理响应（流式或非流式）
            if payload["stream"]:
                # === 流式响应 ===
                async def event_stream():
                    async for line in resp.aiter_lines():
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
                    content=resp.json(),
                    headers={"Access-Control-Allow-Origin": "*"}
                )
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"无法连接 LLM 服务: {e}")
