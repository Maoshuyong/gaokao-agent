"""
从本地数据库导出完整的 seed_gaokao_data.json（含专业分数线）
用于 Render 部署时重建数据库

用法:
    python3 export_seed_data.py
"""
import json
import sys
import logging
from datetime import datetime

sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_FILE = __file__.replace('export_seed_data.py', 'seed_gaokao_data.json')


def export_seed_data():
    """从数据库导出院校 + 录取分数线（含专业分数线）"""
    from db import SessionLocal
    from models import College, Score

    db = SessionLocal()

    # 导出院校
    colleges = db.query(College).all()
    college_list = []
    for c in colleges:
        college_list.append({
            'code': c.code,
            'name': c.name,
            'short_name': c.short_name,
            'province': c.province,
            'city': c.city,
            'level': c.level,
            'type': c.type,
            'is_985': c.is_985,
            'is_211': c.is_211,
            'is_double_first': c.is_double_first,
            'ranking': c.ranking,
            'ranking_type': c.ranking_type,
            'has_master': c.has_master,
            'has_doctor': c.has_doctor,
            'avg_tuition': c.avg_tuition,
            'description': c.description,
        })
    logger.info(f"导出院校: {len(college_list)} 所")

    # 导出录取分数线（含专业分数线）
    scores = db.query(Score).all()
    score_list = []
    major_count = 0
    for s in scores:
        record = {
            'college_id': s.college_id,
            'college_code': s.college_code,
            'college_name': s.college_name,
            'year': s.year,
            'province': s.province,
            'batch': s.batch,
            'category': s.category,
            'min_score': s.min_score,
            'min_rank': s.min_rank,
            'avg_score': s.avg_score,
            'enrollment': s.enrollment,
            'control_score': s.control_score,
        }
        # 如果有专业分数线，一并导出
        if s.major_scores:
            record['major_scores'] = s.major_scores
            major_count += 1
        score_list.append(record)
    logger.info(f"导出录取数据: {len(score_list)} 条（含专业分数线: {major_count} 条）")

    db.close()

    # 写入 JSON
    data = {
        'colleges': college_list,
        'scores': score_list,
        'exported_at': datetime.now().isoformat(),
        'stats': {
            'colleges': len(college_list),
            'scores': len(score_list),
            'scores_with_major': major_count,
        }
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    size_mb = len(json.dumps(data, ensure_ascii=False)) / 1024 / 1024
    logger.info(f"导出完成: {OUTPUT_FILE} ({size_mb:.1f}MB)")
    logger.info(f"统计: {len(college_list)} 所院校, {len(score_list)} 条录取数据, {major_count} 条含专业分数线")


if __name__ == '__main__':
    export_seed_data()
