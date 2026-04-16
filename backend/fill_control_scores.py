# -*- coding: utf-8 -*-
"""
填充省控线数据（control_score）

数据来源：陕西省教育考试院官方公布
用法：python fill_control_scores.py
"""
import sys
sys.path.insert(0, '.')

from db import SessionLocal
from models import Score


# 陕西省 2022-2024 年高考录取最低控制分数线
# 来源：陕西省教育考试院
CONTROL_SCORES = [
    # 2024 年
    {"year": 2024, "province": "陕西", "category": "文科", "batch": "本科一批", "control_score": 488},
    {"year": 2024, "province": "陕西", "category": "文科", "batch": "本科二批", "control_score": 397},
    {"year": 2024, "province": "陕西", "category": "文科", "batch": "专科批", "control_score": 150},
    {"year": 2024, "province": "陕西", "category": "理科", "batch": "本科一批", "control_score": 475},
    {"year": 2024, "province": "陕西", "category": "理科", "batch": "本科二批", "control_score": 372},
    {"year": 2024, "province": "陕西", "category": "理科", "batch": "专科批", "control_score": 150},
    # 2023 年
    {"year": 2023, "province": "陕西", "category": "文科", "batch": "本科一批", "control_score": 489},
    {"year": 2023, "province": "陕西", "category": "文科", "batch": "本科二批", "control_score": 403},
    {"year": 2023, "province": "陕西", "category": "文科", "batch": "专科批", "control_score": 150},
    {"year": 2023, "province": "陕西", "category": "理科", "batch": "本科一批", "control_score": 443},
    {"year": 2023, "province": "陕西", "category": "理科", "batch": "本科二批", "control_score": 336},
    {"year": 2023, "province": "陕西", "category": "理科", "batch": "专科批", "control_score": 150},
    # 2022 年
    {"year": 2022, "province": "陕西", "category": "文科", "batch": "本科一批", "control_score": 484},
    {"year": 2022, "province": "陕西", "category": "文科", "batch": "本科二批", "control_score": 400},
    {"year": 2022, "province": "陕西", "category": "文科", "batch": "专科批", "control_score": 150},
    {"year": 2022, "province": "陕西", "category": "理科", "batch": "本科一批", "control_score": 449},
    {"year": 2022, "province": "陕西", "category": "理科", "batch": "本科二批", "control_score": 344},
    {"year": 2022, "province": "陕西", "category": "理科", "batch": "专科批", "control_score": 150},
]


def fill_control_scores():
    """批量更新省控线到 scores 表中对应批次的记录"""
    db = SessionLocal()
    updated = 0

    for cs in CONTROL_SCORES:
        # 将省控线写入该批次的所有记录
        rows = db.query(Score).filter(
            Score.province == cs["province"],
            Score.year == cs["year"],
            Score.category == cs["category"],
            Score.batch == cs["batch"],
        ).all()

        for row in rows:
            row.control_score = cs["control_score"]
        updated += len(rows)
        print(f"  {cs['year']} {cs['category']} {cs['batch']}: {cs['control_score']}分 ({len(rows)} 条)")

    db.commit()
    print(f"\n✅ 共更新 {updated} 条记录的 control_score")

    # 验证
    for year in [2024, 2023, 2022]:
        for cat in ["文科", "理科"]:
            sample = db.query(Score).filter(
                Score.province == "陕西",
                Score.year == year,
                Score.category == cat,
                Score.batch == "本科一批",
                Score.control_score.isnot(None),
            ).first()
            if sample:
                print(f"  验证: {year} {cat} 本科一批 control_score={sample.control_score}")

    db.close()


if __name__ == "__main__":
    fill_control_scores()
