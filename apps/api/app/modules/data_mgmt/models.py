from app.core.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func


class DataRetentionConfig(Base):
    __tablename__ = "data_retention_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), nullable=False, unique=True)
    max_age_days = Column(Integer, nullable=True)
    max_records = Column(Integer, nullable=True)
    keep_saved = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)
    config_json = Column(Text, nullable=True)
    last_purge_at = Column(DateTime, nullable=True)
    last_purge_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
