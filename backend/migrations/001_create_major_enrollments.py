#!/usr/bin/env python3
"""
迁移脚本：创建 major_enrollments 表
运行方式：
  cd /Users/fengweitao/WorkBuddy/20260414000511/gaokao-agent/backend
  python migrations/001_create_major_enrollments.py
"""

import sys
import os

# 将 backend 目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import engine, Base
from models.major_enrollment import MajorEnrollment


def run_migration():
    """执行迁移：创建 major_enrollments 表"""
    print("开始执行迁移：创建 major_enrollments 表...")

    # checkfirst=True：表已存在则跳过，安全幂等
    MajorEnrollment.__table__.create(bind=engine, checkfirst=True)

    # 验证表是否创建成功
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "major_enrollments" in tables:
        print("✅ major_enrollments 表已就绪")
        # 打印表结构
        columns = inspector.get_columns("major_enrollments")
        print(f"   字段数: {len(columns)}")
        for col in columns:
            print(f"   - {col['name']}: {col['type']}")
    else:
        print("❌ 表创建失败，请检查错误信息")
        return False

    return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
