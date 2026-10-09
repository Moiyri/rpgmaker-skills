"""加载正式数据库后端，供事件脚本统一校验与写入。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3] / 'rpgmaker-database/scripts/database.py'
spec = importlib.util.spec_from_file_location('events_database', BACKEND)
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)
require, fields = db.require, db.fields
