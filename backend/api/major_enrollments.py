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
