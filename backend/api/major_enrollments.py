"""
专业级招生数据 API

查询 2025 年专业级招生数据（来自 major_enrollments 表）
包含：招生计划、历年录取分数、院校信息
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional, List, Dict, Any

from db import get_db

router = APIRouter(prefix="/api/v1/major-enrollments", tags=["major-enrollments"])


class MajorEnrollmentResponse(BaseModel):
    """专业招生数据响应"""
    id: int
    college_name: str
    college_code: str
    year: int
    province: str
    batch: Optional[str]
    category: Optional[str]
    major_group: Optional[str]
    major_group_code: Optional[str]
    major_name: str
    major_code: Optional[str]
    major_category: Optional[str]
    major_note: Optional[str]
    subject_requirement: Optional[str]
    is_new: Optional[bool]
    plan_count: Optional[int]
    duration: Optional[int]
    tuition: Optional[str]
    score_2025_min: Optional[int]
    rank_2025_min: Optional[int]
    enrollment_2025: Optional[int]
    score_2024_min: Optional[int]
    rank_2024_min: Optional[int]
    enrollment_2024: Optional[int]
    score_2023_min: Optional[int]
    rank_2023_min: Optional[int]
    enrollment_2023: Optional[int]
    score_2022_min: Optional[int]
    rank_2022_min: Optional[int]
    enrollment_2022: Optional[int]
    college_rank: Optional[int]
    double_first_class: Optional[bool]
    college_city: Optional[str]


@router.get("/", response_model=List[MajorEnrollmentResponse])
async def search_major_enrollments(
    college_name: Optional[str] = Query(None, description="院校名称关键词"),
    major_name: Optional[str] = Query(None, description="专业名称关键词"),
    province: str = Query("陕西", description="省份"),
    year: int = Query(2025, description="年份"),
    batch: Optional[str] = Query(None, description="批次"),
    category: Optional[str] = Query(None, description="科类"),
    min_score: Optional[int] = Query(None, description="最低分数"),
    max_score: Optional[int] = Query(None, description="最高分数"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    搜索专业级招生数据
    
    支持按院校、专业、分数范围筛选
    """
    # 使用原始 SQL（因为 major_enrollments 表没有 ORM 模型）
    from sqlalchemy import text
    
    conditions = ["1=1"]
    params = {}
    
    if college_name:
        conditions.append("college_name LIKE :college_name")
        params["college_name"] = f"%{college_name}%"
    
    if major_name:
        conditions.append("major_name LIKE :major_name")
        params["major_name"] = f"%{major_name}%"
    
    if province:
        conditions.append("province = :province")
        params["province"] = province
    
    if year:
        conditions.append("year = :year")
        params["year"] = year
    
    if batch:
        conditions.append("batch = :batch")
        params["batch"] = batch
    
    if category:
        conditions.append("category LIKE :category")
        params["category"] = f"%{category}%"
    
    if min_score:
        conditions.append("""
            (score_2025_min >= :min_score 
             OR score_2024_min >= :min_score 
             OR score_2023_min >= :min_score)
        """)
        params["min_score"] = min_score
    
    if max_score:
        conditions.append("""
            (score_2025_min <= :max_score 
             OR score_2024_min <= :max_score 
             OR score_2023_min <= :max_score)
        """)
        params["max_score"] = max_score
    
    where_clause = " AND ".join(conditions)
    
    # 查询
    offset = (page - 1) * page_size
    
    sql = text(f"""
        SELECT 
            id, college_name, college_code, year, province, batch, category,
            major_group, major_group_code, major_name, major_code, major_category,
            major_note, subject_requirement, is_new, plan_count, duration, tuition,
            score_2025_min, rank_2025_min, enrollment_2025,
            score_2024_min, rank_2024_min, enrollment_2024,
            score_2023_min, rank_2023_min, enrollment_2023,
            score_2022_min, rank_2022_min, enrollment_2022,
            college_rank, double_first_class, college_city
        FROM major_enrollments
        WHERE {where_clause}
        ORDER BY 
            CASE WHEN score_2024_min IS NOT NULL THEN 0 ELSE 1 END,
            score_2024_min DESC
        LIMIT :limit OFFSET :offset
    """)
    
    params["limit"] = page_size
    params["offset"] = offset
    
    result = db.execute(sql, params).fetchall()
    
    return [
        MajorEnrollmentResponse(
            id=row[0],
            college_name=row[1],
            college_code=row[2],
            year=row[3],
            province=row[4],
            batch=row[5],
            category=row[6],
            major_group=row[7],
            major_group_code=row[8],
            major_name=row[9],
            major_code=row[10],
            major_category=row[11],
            major_note=row[12],
            subject_requirement=row[13],
            is_new=bool(row[14]) if row[14] is not None else None,
            plan_count=row[15],
            duration=row[16],
            tuition=row[17],
            score_2025_min=row[18],
            rank_2025_min=row[19],
            enrollment_2025=row[20],
            score_2024_min=row[21],
            rank_2024_min=row[22],
            enrollment_2024=row[23],
            score_2023_min=row[24],
            rank_2023_min=row[25],
            enrollment_2023=row[26],
            score_2022_min=row[27],
            rank_2022_min=row[28],
            enrollment_2022=row[29],
            college_rank=row[30],
            double_first_class=bool(row[31]) if row[31] is not None else None,
            college_city=row[32]
        )
        for row in result
    ]


@router.get("/college/{college_name}", response_model=List[MajorEnrollmentResponse])
async def get_college_major_enrollments(
    college_name: str,
    year: int = Query(2025, description="年份"),
    province: str = Query("陕西", description="省份"),
    db: Session = Depends(get_db)
):
    """
    获取指定院校的专业级招生数据
    """
    from sqlalchemy import text
    
    sql = text("""
        SELECT 
            id, college_name, college_code, year, province, batch, category,
            major_group, major_group_code, major_name, major_code, major_category,
            major_note, subject_requirement, is_new, plan_count, duration, tuition,
            score_2025_min, rank_2025_min, enrollment_2025,
            score_2024_min, rank_2024_min, enrollment_2024,
            score_2023_min, rank_2023_min, enrollment_2023,
            score_2022_min, rank_2022_min, enrollment_2022,
            college_rank, double_first_class, college_city
        FROM major_enrollments
        WHERE college_name LIKE :college_name 
          AND province = :province 
          AND year = :year
        ORDER BY 
            CASE WHEN score_2024_min IS NOT NULL THEN 0 ELSE 1 END,
            score_2024_min DESC
    """)
    
    result = db.execute(sql, {
        "college_name": f"%{college_name}%",
        "province": province,
        "year": year
    }).fetchall()
    
    if not result:
        raise HTTPException(status_code=404, detail="未找到该院校的专业招生数据")
    
    return [
        MajorEnrollmentResponse(
            id=row[0],
            college_name=row[1],
            college_code=row[2],
            year=row[3],
            province=row[4],
            batch=row[5],
            category=row[6],
            major_group=row[7],
            major_group_code=row[8],
            major_name=row[9],
            major_code=row[10],
            major_category=row[11],
            major_note=row[12],
            subject_requirement=row[13],
            is_new=bool(row[14]) if row[14] is not None else None,
            plan_count=row[15],
            duration=row[16],
            tuition=row[17],
            score_2025_min=row[18],
            rank_2025_min=row[19],
            enrollment_2025=row[20],
            score_2024_min=row[21],
            rank_2024_min=row[22],
            enrollment_2024=row[23],
            score_2023_min=row[24],
            rank_2023_min=row[25],
            enrollment_2023=row[26],
            score_2022_min=row[27],
            rank_2022_min=row[28],
            enrollment_2022=row[29],
            college_rank=row[30],
            double_first_class=bool(row[31]) if row[31] is not None else None,
            college_city=row[32]
        )
        for row in result
    ]


@router.get("/stats")
async def get_major_enrollments_stats(
    province: str = Query("陕西", description="省份"),
    year: int = Query(2025, description="年份"),
    db: Session = Depends(get_db)
):
    """
    获取专业招生数据统计信息
    """
    from sqlalchemy import text
    
    sql = text("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT college_name) as college_count,
            COUNT(DISTINCT major_name) as major_count,
            COUNT(CASE WHEN score_2024_min IS NOT NULL THEN 1 END) as has_score_count
        FROM major_enrollments
        WHERE province = :province AND year = :year
    """)
    
    result = db.execute(sql, {"province": province, "year": year}).fetchone()
    
    return {
        "total": result[0],
        "college_count": result[1],
        "major_count": result[2],
        "has_score_count": result[3],
        "province": province,
        "year": year
    }


# MBTI 类型 → 专业关键词映射（从 mbti.js 提取）
MBTI_MAJOR_MAPPING = {
    "INTJ": ["计算机", "人工智能", "数学", "物理", "法学", "金融工程"],
    "INTP": ["计算机", "哲学", "数学", "心理学", "数据科学"],
    "ENTJ": ["管理", "经济学", "法学", "金融", "工商管理"],
    "ENTP": ["新闻", "市场营销", "创业", "产品设计"],
    "INFJ": ["心理学", "教育学", "社会工作", "临床医学", "文学"],
    "INFP": ["文学", "艺术", "心理学", "社会工作", "哲学"],
    "ENFJ": ["教育学", "人力资源", "公共关系", "临床心理学"],
    "ENFP": ["新闻", "广告", "公共关系", "旅游管理"],
    "ISTJ": ["会计", "土木工程", "计算机", "药学", "机械工程"],
    "ISFJ": ["护理", "教育学", "会计", "人力资源", "药学"],
    "ESTJ": ["工商管理", "会计", "法学", "土木工程", "项目管理"],
    "ESFJ": ["护理", "教育学", "酒店管理", "社会工作", "人力资源"],
    "ISTP": ["机械工程", "电子工程", "计算机", "汽车工程", "航空"],
    "ISFP": ["视觉传达", "环境设计", "音乐", "摄影", "手工艺"],
    "ESTP": ["市场营销", "体育管理", "金融", "销售管理"],
    "ESFP": ["表演艺术", "旅游管理", "酒店管理", "活动策划", "运动训练"],
}


class MBTIMajorRecommendation(BaseModel):
    """MBTI 专业推荐响应"""
    mbti_type: str
    mbti_name: str
    major_name: str
    match_reason: str
    related_colleges: List[str]
    min_score_2024: Optional[int] = None
    avg_score_2024: Optional[float] = None


@router.get("/recommend-by-mbti", response_model=List[MBTIMajorRecommendation])
async def recommend_majors_by_mbti(
    mbti_type: str = Query(..., description="MBTI 类型（如 INTJ、ENFP）", regex="^[EI][SN][TF][JP]$"),
    province: str = Query("陕西", description="省份"),
    year: int = Query(2025, description="年份"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db)
):
    """
    根据 MBTI 类型推荐专业
    
    基于 MBTI 性格特点，从专业招生数据中匹配相关专业
    """
    # 验证 MBTI 类型
    mbti_type = mbti_type.upper()
    if mbti_type not in MBTI_MAJOR_MAPPING:
        raise HTTPException(status_code=400, detail=f"无效的 MBTI 类型：{mbti_type}")
    
    # 获取该 MBTI 对应的专业关键词
    major_keywords = MBTI_MAJOR_MAPPING.get(mbti_type, [])
    
    if not major_keywords:
        return []
    
    from sqlalchemy import text
    
    # 构建 OR 条件（匹配任一关键词）
    or_conditions = []
    params = {"province": province, "year": year}
    
    for idx, keyword in enumerate(major_keywords):
        or_conditions.append(f"major_name LIKE :kw{idx}")
        params[f"kw{idx}"] = f"%{keyword}%"
    
    where_clause = " OR ".join(or_conditions)
    
    sql = text(f"""
        SELECT 
            major_name,
            AVG(CASE WHEN score_2024_min IS NOT NULL THEN score_2024_min END) as avg_score,
            MIN(score_2024_min) as min_score,
            COUNT(DISTINCT college_name) as college_count
        FROM major_enrollments
        WHERE province = :province 
          AND year = :year
          AND ({where_clause})
        GROUP BY major_name
        ORDER BY 
            college_count DESC,
            avg_score DESC
        LIMIT :limit
    """)

    params["limit"] = limit
    result = db.execute(sql, params).fetchall()

    mbti_names = {
        "INTJ": "建筑师", "INTP": "逻辑学家", "ENTJ": "指挥官", "ENTP": "辩论家",
        "INFJ": "提倡者", "INFP": "调停者", "ENFJ": "主人公", "ENFP": "竞选者",
        "ISTJ": "物流师", "ISFJ": "守卫者", "ESTJ": "总经理", "ESFJ": "执政官",
        "ISTP": "鉴赏家", "ISFP": "探险家", "ESTP": "企业家", "ESFP": "表演者",
    }

    match_reasons = {
        "INTJ": "善于战略思维和长远规划，适合需要深度思考的专业",
        "INTP": "热衷探索理论和抽象概念，适合需要逻辑分析的专业",
        "ENTJ": "天生的领导者，善于推动项目，适合需要决策力的专业",
        "ENTP": "思维活跃，善于创新，适合需要灵活思维的专业",
        "INFJ": "有强烈的理想主义，善于洞察他人，适合助人专业",
        "INFP": "追求真实和意义，内心丰富，适合创造性专业",
        "ENFJ": "善于激励他人，有强烈责任感，适合教育管理专业",
        "ENFP": "热情创造力强，善于发现可能性，适合传媒艺术专业",
        "ISTJ": "可靠务实，有条理，适合需要精细管理的专业",
        "ISFJ": "温暖勤勉，默默奉献，适合护理教育专业",
        "ESTJ": "组织力强，果断务实，适合工商项目管理专业",
        "ESFJ": "社交天赋强，善于营造和谐，适合护理教育专业",
        "ISTP": "冷静务实，动手能力强，适合工程技术专业",
        "ISFP": "温和有艺术气质，追求和谐，适合设计艺术专业",
        "ESTP": "行动力强，善于应变，适合市场营销专业",
        "ESFP": "乐观热情，善于表现，适合表演艺术专业",
    }

    return [
        MBTIMajorRecommendation(
            mbti_type=mbti_type,
            mbti_name=mbti_names.get(mbti_type, ""),
            major_name=row[0],
            match_reason=match_reasons.get(mbti_type, ""),
            related_colleges=[],  # TODO: 后续通过单独查询获取
            min_score_2024=row[2],
            avg_score_2024=round(row[1], 1) if row[1] else None
        )
        for row in result
    ]


# ═══════════════════════════════════════════════════════════
# 冲稳保推荐 API
# ═══════════════════════════════════════════════════════════

class CollegeRecommendation(BaseModel):
    """冲稳保院校推荐项"""
    college_name: str
    college_code: Optional[str] = None
    batch: Optional[str] = None
    min_score_2024: Optional[int] = None
    min_rank_2024: Optional[int] = None
    avg_score_2024: Optional[int] = None
    min_score_2023: Optional[int] = None
    min_rank_2023: Optional[int] = None
    min_score_2022: Optional[int] = None
    min_rank_2022: Optional[int] = None
    control_score: Optional[int] = None
    enrollment: Optional[int] = None
    rank_gap: Optional[int] = None          # 位次差（考生位次 - 院校位次）
    top_majors: Optional[List[str]] = None   # 分数较低的热门专业
    risk_level: str = ""                     # 冲/稳/保
    tags: Optional[List[str]] = None         # 985/211 等标签


class ReachMatchSafetyResponse(BaseModel):
    """冲稳保推荐响应"""
    student_score: Optional[int] = None
    student_rank: Optional[int] = None
    province: str
    category: str
    estimated_rank: Optional[int] = None      # 由分数估算的位次
    rank_source: str = ""                     # "用户提供" / "分数估算"
    reach: List[CollegeRecommendation] = []   # 冲
    match: List[CollegeRecommendation] = []   # 稳
    safety: List[CollegeRecommendation] = []  # 保
    total_found: int = 0
    note: str = ""


@router.get("/recommend-rms", response_model=ReachMatchSafetyResponse)
async def recommend_reach_match_safety(
    province: str = Query("陕西", description="省份"),
    category: str = Query(..., description="科类（文科/理科/物理类/历史类）"),
    score: Optional[int] = Query(None, description="高考分数"),
    rank: Optional[int] = Query(None, description="省排名（位次）"),
    year: int = Query(2024, description="参考年份（录取数据年份）"),
    batch: Optional[str] = Query(None, description="批次（默认本科一批）"),
    reach_limit: int = Query(10, ge=1, le=50, description="冲的数量"),
    match_limit: int = Query(15, ge=1, le=50, description="稳的数量"),
    safety_limit: int = Query(10, ge=1, le=50, description="保的数量"),
    db: Session = Depends(get_db)
):
    """
    冲稳保院校推荐

    核心逻辑（基于位次匹配）：
    - 冲（Reach）：院校最低位次比考生位次高 300~3000 名
    - 稳（Match）：院校最低位次在考生位次 ±300 名
    - 保（Safety）：院校最低位次比考生位次低 300~5000 名

    优先使用位次（rank），如果没有则通过一分一段表从分数估算位次。
    """
    from sqlalchemy import text as _text
    import json as _json

    def T(sql_str):
        """Shortcut for sqlalchemy.text"""
        return _text(sql_str)

    # ─── 1. 确定位次 ───
    student_rank = None
    rank_source = ""
    estimated_rank = None

    if rank and rank > 0:
        student_rank = rank
        rank_source = "用户提供"
    elif score and score > 0:
        # 通过一分一段表反查位次
        category_for_table = category
        if category in ("物理/不限", "物理/化学", "物理/生物", "物理/地理",
                        "物理/思想政治", "物理/化学+生物"):
            category_for_table = "物理类"
        elif category in ("历史/不限", "历史/思想政治", "历史/地理", "历史/生物"):
            category_for_table = "历史类"

        rank_sql = T("""
            SELECT cumulative_count FROM score_rank_tables
            WHERE province = :province AND year = :year AND category = :category AND score = :score
            LIMIT 1
        """)
        rank_result = db.execute(rank_sql, {
            "province": province, "year": year, "category": category_for_table, "score": score
        }).fetchone()

        if rank_result:
            student_rank = rank_result[0]
            estimated_rank = student_rank
            rank_source = "分数估算"
        else:
            # 找最近的分数
            nearest_sql = T("""
                SELECT score, cumulative_count FROM score_rank_tables
                WHERE province = :province AND year = :year AND category = :category AND score <= :score
                ORDER BY score DESC LIMIT 1
            """)
            nearest = db.execute(nearest_sql, {
                "province": province, "year": year,
                "category": category_for_table, "score": score
            }).fetchone()
            if nearest:
                student_rank = nearest[1]
                estimated_rank = student_rank
                rank_source = "分数估算（近似）"

    if not student_rank:
        return ReachMatchSafetyResponse(
            province=province,
            category=category,
            note="无法确定位次，请提供省排名（位次）或有效的分数"
        )

    # ─── 2. 查询院校录取数据 ───
    query_batch = batch or "本科一批"

    # 科类映射
    score_category = category
    if category in ("物理/不限", "物理/化学", "物理/生物", "物理/地理",
                    "物理/思想政治", "物理/化学+生物"):
        score_category = "理科"
    elif category in ("历史/不限", "历史/思想政治", "历史/地理", "历史/生物"):
        score_category = "文科"

    categories_to_try = [score_category]
    if score_category in ("理科", "文科"):
        new_cat = "物理类" if score_category == "理科" else "历史类"
        categories_to_try.append(new_cat)

    all_results = []
    for cat in categories_to_try:
        sql = T("""
            SELECT
                college_name, college_code, batch,
                MIN(min_score) FILTER (WHERE year = 2024) as s24_min,
                MIN(min_rank) FILTER (WHERE year = 2024) as r24_min,
                AVG(min_score) FILTER (WHERE year = 2024) as s24_avg,
                MIN(min_score) FILTER (WHERE year = 2023) as s23_min,
                MIN(min_rank) FILTER (WHERE year = 2023) as r23_min,
                MIN(min_score) FILTER (WHERE year = 2022) as s22_min,
                MIN(min_rank) FILTER (WHERE year = 2022) as r22_min,
                MAX(control_score) as ctrl_score,
                SUM(enrollment) as total_enrollment,
                MIN(min_rank) as best_rank
            FROM scores
            WHERE province = :province
              AND category = :category
              AND batch = :batch
              AND min_rank IS NOT NULL
              AND min_rank > 0
            GROUP BY college_name, college_code, batch
            HAVING best_rank IS NOT NULL
            ORDER BY best_rank ASC
        """)

        try:
            results = db.execute(sql, {
                "province": province, "category": cat, "batch": query_batch
            }).fetchall()
            all_results.extend(results)
        except Exception as e:
            # FILTER 语法可能不被所有 SQLite 版本支持，降级处理
            if "FILTER" in str(e):
                sql_fallback = T("""
                    SELECT
                        college_name, college_code, batch,
                        NULL as s24_min, NULL as r24_min, NULL as s24_avg,
                        NULL as s23_min, NULL as r23_min,
                        NULL as s22_min, NULL as r22_min,
                        NULL as ctrl_score, NULL as total_enrollment,
                        MIN(min_rank) as best_rank
                    FROM scores
                    WHERE province = :province
                      AND category = :category
                      AND batch = :batch
                      AND min_rank IS NOT NULL AND min_rank > 0
                    GROUP BY college_name, college_code, batch
                    HAVING best_rank IS NOT NULL
                    ORDER BY best_rank ASC
                """)
                results = db.execute(sql_fallback, {
                    "province": province, "category": cat, "batch": query_batch
                }).fetchall()
                all_results.extend(results)

    # 去重（按院校名去重，保留位次最好的）
    seen = {}
    for row in all_results:
        name = row[0]
        if name not in seen or (row[12] is not None and (seen[name][12] is None or row[12] < seen[name][12])):
            seen[name] = row
    unique_results = list(seen.values())

    # ─── 3. 获取院校标签 ───
    tags_map = {}
    if unique_results:
        college_names = [r[0] for r in unique_results[:200]]
        placeholders = ",".join(
            f"'{n.replace(chr(39), chr(39)+chr(39))}'" for n in college_names
        )
        try:
            tags_results = db.execute(T(f"""
                SELECT name,
                    CASE WHEN is_985 = 1 THEN '985' ELSE NULL END,
                    CASE WHEN is_211 = 1 THEN '211' ELSE NULL END,
                    CASE WHEN is_double_first = 1 THEN '双一流' ELSE NULL END
                FROM colleges WHERE name IN ({placeholders})
            """)).fetchall()
            for tr in tags_results:
                tags = [t for t in [tr[1], tr[2], tr[3]] if t]
                tags_map[tr[0]] = tags
        except Exception:
            pass

    # ─── 4. 分类：冲/稳/保 ───
    reach_items = []
    match_items = []
    safety_items = []

    REACH_MAX = 5000    # 冲：位次比考生高 500~5000 名
    REACH_MIN = 500     # 冲的最小差距
    MATCH_RANGE = 1000  # 稳：±1000 名
    SAFETY_MIN = 1000   # 保：位次比考生低 1000+
    SAFETY_MAX = 8000   # 保的范围上限

    for row in unique_results:
        college_name = row[0]
        best_rank = row[12]
        if best_rank is None:
            continue

        rank_gap = student_rank - best_rank

        # 提取分数较低的热门专业
        top_majors = []
        try:
            cat_list = ",".join(f"'{c}'" for c in categories_to_try)
            major_result = db.execute(T(f"""
                SELECT major_scores FROM scores
                WHERE college_name = :name AND province = :province
                  AND category IN ({cat_list}) AND batch = :batch
                  AND major_scores IS NOT NULL AND major_scores != "[]"
                LIMIT 1
            """), {"name": college_name, "province": province, "batch": query_batch}).fetchone()
            if major_result:
                majors_data = _json.loads(major_result[0])
                sorted_majors = sorted(majors_data, key=lambda x: x.get("score", 999))
                top_majors = [m["major"] for m in sorted_majors[:5] if "major" in m]
        except Exception:
            pass

        item = CollegeRecommendation(
            college_name=college_name,
            college_code=row[1],
            batch=row[2],
            min_score_2024=row[3],
            min_rank_2024=row[4],
            avg_score_2024=int(row[5]) if row[5] else None,
            min_score_2023=row[6],
            min_rank_2023=row[7],
            min_score_2022=row[8],
            min_rank_2022=row[9],
            control_score=row[10],
            enrollment=row[11],
            rank_gap=rank_gap,
            top_majors=top_majors[:5] if top_majors else None,
            tags=tags_map.get(college_name, None),
            risk_level=""
        )

        if rank_gap < -REACH_MIN and rank_gap >= -REACH_MAX:
            item.risk_level = "冲"
            reach_items.append(item)
        elif -MATCH_RANGE <= rank_gap <= MATCH_RANGE:
            item.risk_level = "稳"
            match_items.append(item)
        elif rank_gap > SAFETY_MIN and rank_gap <= SAFETY_MAX:
            item.risk_level = "保"
            safety_items.append(item)

    # 排序
    reach_items.sort(key=lambda x: x.rank_gap or 0, reverse=True)
    match_items.sort(key=lambda x: abs(x.rank_gap or 0))
    safety_items.sort(key=lambda x: x.rank_gap or 0)

    total = len(reach_items) + len(match_items) + len(safety_items)

    note_parts = []
    if estimated_rank:
        note_parts.append(f"位次由分数{score}分估算而得，仅供参考")
    if not reach_items:
        note_parts.append("没有找到合适的冲刺院校（可能位次较高或数据不足）")
    if not safety_items:
        note_parts.append("没有找到保底院校，建议适当扩大保底范围")

    return ReachMatchSafetyResponse(
        student_score=score,
        student_rank=student_rank,
        province=province,
        category=category,
        estimated_rank=estimated_rank,
        rank_source=rank_source,
        reach=reach_items[:reach_limit],
        match=match_items[:match_limit],
        safety=safety_items[:safety_limit],
        total_found=total,
        note="；".join(note_parts) if note_parts else "推荐完成"
    )
