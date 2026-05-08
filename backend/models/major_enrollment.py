"""
专业招生计划 ORM 模型
对应 major_enrollments 宽表（71列），包含院校信息、专业信息、历年录取分数、招生计划等。

注：此表为非规范化设计，便于快速查询，避免多表 JOIN。
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index
from sqlalchemy.sql import func
from db.database import Base


class MajorEnrollment(Base):
    """专业招生计划宽表（ORM 模型）"""
    __tablename__ = "major_enrollments"

    id = Column(Integer, primary_key=True, index=True)

    # ===== 院校信息 =====
    college_name = Column(String(100), index=True, comment="院校名称")
    college_code = Column(String(10), index=True, comment="院校代码")
    college_province = Column(String(20), comment="院校所在省份")
    college_city = Column(String(50), comment="院校所在城市")
    city_level = Column(String(50), comment="城市等级（一线/新一线等）")
    college_type = Column(String(50), comment="院校类型（综合/理工/师范等）")
    college_nature = Column(String(50), comment="办学性质（公办/民办/中外合办）")
    college_department = Column(String(100), comment="主管部门")
    college_tags = Column(String(100), comment="院校标签")
    college_level = Column(String(50), comment="院校层次（本科/专科）")
    college_rank = Column(Integer, comment="院校排名")
    college_intro = Column(Text, comment="院校简介")
    double_first_class = Column(Boolean, comment="是否双一流")
    discipline_evaluation = Column(String(100), comment="学科评估")
    national_feature = Column(Boolean, comment="是否国家级特色专业")
    soft_rank = Column(Integer, comment="软科排名")

    # ===== 招生基本信息 =====
    year = Column(Integer, index=True, comment="招生年份")
    province = Column(String(20), index=True, comment="招生省份")
    batch = Column(String(20), comment="批次（本科批/本科一批等）")
    category = Column(String(50), index=True, comment="科类（物理类/历史类/文科/理科）")

    # ===== 专业组 =====
    major_group = Column(String(50), comment="专业组名称")
    major_group_code = Column(String(10), comment="专业组代码")
    group_majors = Column(Text, comment="专业组内专业列表（JSON）")

    # ===== 专业信息 =====
    major_name = Column(String(100), index=True, comment="专业名称")
    major_code = Column(String(10), comment="专业代码")
    major_category = Column(String(50), comment="专业类别")
    major_note = Column(Text, comment="专业备注")
    subject_requirement = Column(String(100), comment="选科要求")
    is_new = Column(Boolean, comment="是否新增专业")
    major_honor = Column(String(200), comment="专业荣誉")

    # ===== 招生计划 =====
    plan_count = Column(Integer, comment="计划招生人数")
    enrollment_2025 = Column(Integer, comment="2025年实际录取人数")
    enrollment_2024 = Column(Integer, comment="2024年实际录取人数")
    enrollment_2023 = Column(Integer, comment="2023年实际录取人数")
    enrollment_2022 = Column(Integer, comment="2022年实际录取人数")
    enrollment_plan = Column(Text, comment="招生计划说明（JSON）")

    # ===== 学制与学费 =====
    duration = Column(Integer, comment="学制（年）")
    tuition = Column(String(20), comment="学费（元/年）")

    # ===== 2025年录取分数 =====
    score_2025_min = Column(Integer, comment="2025年最低分")
    rank_2025_min = Column(Integer, comment="2025年最低位次")

    # ===== 2024年录取分数 =====
    score_2024_max = Column(Integer, comment="2024年最高分")
    rank_2024_max = Column(Integer, comment="2024年最高位次")
    score_2024_avg = Column(Integer, comment="2024年平均分")
    rank_2024_avg = Column(Integer, comment="2024年平均位次")
    score_2024_min = Column(Integer, comment="2024年最低分")
    rank_2024_min = Column(Integer, comment="2024年最低位次")

    # ===== 2023年录取分数 =====
    score_2023_max = Column(Integer, comment="2023年最高分")
    rank_2023_max = Column(Integer, comment="2023年最高位次")
    score_2023_avg = Column(Integer, comment="2023年平均分")
    rank_2023_avg = Column(Integer, comment="2023年平均位次")
    score_2023_min = Column(Integer, comment="2023年最低分")
    rank_2023_min = Column(Integer, comment="2023年最低位次")

    # ===== 2022年录取分数 =====
    score_2022_max = Column(Integer, comment="2022年最高分")
    rank_2022_max = Column(Integer, comment="2022年最高位次")
    score_2022_avg = Column(Integer, comment="2022年平均分")
    rank_2022_avg = Column(Integer, comment="2022年平均位次")
    score_2022_min = Column(Integer, comment="2022年最低分")
    rank_2022_min = Column(Integer, comment="2022年最低位次")

    # ===== 升学信息 =====
    has_master = Column(Boolean, comment="是否有硕士点")
    has_doctor = Column(Boolean, comment="是否有博士点")
    master_count = Column(Integer, comment="硕士点数量")
    master_majors = Column(Text, comment="硕士专业列表（JSON）")
    doctor_count = Column(Integer, comment="博士点数量")
    doctor_majors = Column(Text, comment="博士专业列表（JSON）")
    baoyan_rate = Column(String(20), comment="保研率")

    # ===== 其他 =====
    department_setting = Column(Text, comment="院系设置（JSON）")
    rename_merge = Column(Text, comment="院校更名合并历史")
    transfer_major = Column(Text, comment="转专业政策")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ===== 复合索引 =====
    __table_args__ = (
        Index("idx_me_year_province", "year", "province"),
        Index("idx_me_college_year", "college_code", "year"),
        Index("idx_me_major_year", "major_name", "year"),
        Index("idx_me_batch_category", "batch", "category"),
    )
