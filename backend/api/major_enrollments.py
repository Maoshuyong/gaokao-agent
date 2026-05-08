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
            COUNT(DISTINCT college_name) as college_count,
            GROUP_CONCAT(DISTINCT college_name, '、') as colleges
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
            related_colleges=row[3].split("、") if row[3] else [],
            min_score_2024=row[2],
            avg_score_2024=round(row[1], 1) if row[1] else None
        )
        for row in result
    ]
