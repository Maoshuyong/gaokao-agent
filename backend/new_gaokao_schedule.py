"""
新高考改革时间表

根据教育部公布的高考改革方案，各省份实施新高考的时间不同。
此文件用于 gaokao-agent 中根据年份和省份判断应该使用哪种科类映射规则。

时间表格式：
- key: 省份名称
- value: 实施新高考的年份（该年份及之后使用新高考规则）
"""

# 新高考改革实施时间表（第一批 - 第五批）
# 第一批（2014年启动，2017年首次实施）
FIRST_BATCH = {
    '浙江': 2017,
    '上海': 2017,
}

# 第二批（2017年启动，2020年首次实施）
SECOND_BATCH = {
    '北京': 2020,
    '天津': 2020,
    '山东': 2020,
    '海南': 2020,
}

# 第三批（2018年启动，2021年首次实施）
THIRD_BATCH = {
    '河北': 2021,
    '辽宁': 2021,
    '江苏': 2021,
    '福建': 2021,
    '湖北': 2021,
    '湖南': 2021,
    '广东': 2021,
    '重庆': 2021,
}

# 第四批（2021年启动，2024年首次实施）
FOURTH_BATCH = {
    '吉林': 2024,
    '黑龙江': 2024,
    '安徽': 2024,
    '江西': 2024,
    '广西': 2024,
    '贵州': 2024,
    '甘肃': 2024,
}

# 第五批（2022年启动，2025年首次实施）
FIFTH_BATCH = {
    '河南': 2025,
    '陕西': 2025,
    '山西': 2025,
    '内蒙古': 2025,
    '四川': 2025,
    '云南': 2025,
    '宁夏': 2025,
    '青海': 2025,
}

# 合并所有批次
NEW_GAOKAO_SCHEDULE = {}
NEW_GAOKAO_SCHEDULE.update(FIRST_BATCH)
NEW_GAOKAO_SCHEDULE.update(SECOND_BATCH)
NEW_GAOKAO_SCHEDULE.update(THIRD_BATCH)
NEW_GAOKAO_SCHEDULE.update(FOURTH_BATCH)
NEW_GAOKAO_SCHEDULE.update(FIFTH_BATCH)


def is_new_gaokao(province: str, year: int) -> bool:
    """
    判断某省份在某年是否实施新高考

    Args:
        province: 省份名称（例如：'陕西'、'江苏'）
        year: 高考年份（例如：2026）

    Returns:
        bool: 该年份是否实施新高考
    """
    if province in NEW_GAOKAO_SCHEDULE:
        return year >= NEW_GAOKAO_SCHEDULE[province]
    return False


def get_category_mapping(province: str, year: int, category: str) -> str:
    """
    根据省份和年份获取正确的科类映射

    新高考省份：
    - 物理类 → 物理类（不映射）
    - 历史类 → 历史类（不映射）

    老高考省份：
    - 理科 → 理科
    - 文科 → 文科

    Args:
        province: 省份名称
        year: 高考年份
        category: 用户输入的科类

    Returns:
        str: 数据库查询使用的科类
    """
    if is_new_gaokao(province, year):
        # 新高考：直接使用原科类（物理类/历史类）
        return category
    else:
        # 老高考：映射（如果有需要）
        # 目前新老高考科类名称一致，无需映射
        return category


# 测试代码
if __name__ == '__main__':
    # 测试：陕西 2025 年是否新高考
    print(f"陕西 2024年新高考：{is_new_gaokao('陕西', 2024)}")  # False
    print(f"陕西 2025年新高考：{is_new_gaokao('陕西', 2025)}")  # True
    print(f"陕西 2026年新高考：{is_new_gaokao('陕西', 2026)}")  # True

    print(f"\n江苏 2020年新高考：{is_new_gaokao('江苏', 2020)}")  # False
    print(f"江苏 2021年新高考：{is_new_gaokao('江苏', 2021)}")  # True

    print(f"\n浙江 2016年新高考：{is_new_gaokao('浙江', 2016)}")  # False
    print(f"浙江 2017年新高考：{is_new_gaokao('浙江', 2017)}")  # True
