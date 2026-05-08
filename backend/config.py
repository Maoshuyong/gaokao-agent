"""
应用配置
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 项目基础
    PROJECT_NAME: str = "高考志愿填报专家 - 数据服务"
    VERSION: str = "2.0.0"
    DEBUG: bool = True

    # 数据库（连接字符串，不是下载 URL）
    # 由 start.sh 设置正确的数据库连接字符串
    # 注意：不要设置环境变量 DATABASE_URL（会冲突），改用 DATABASE_FILE
    DATABASE_FILE: str = "sqlite:///./data/gaokao.db"
    
    @property
    def DATABASE_URL(self) -> str:
        """动态获取数据库连接字符串（优先从环境变量读取，支持 start.sh 设置）"""
        return os.environ.get("DATABASE_URL", self.DATABASE_FILE)

    # 数据路径
    DATA_DIR: str = "./data"

    # 服务端口 — Render 等云平台通过 PORT 环境变量注入
    PORT: int = int(os.environ.get("PORT", "8000"))

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
