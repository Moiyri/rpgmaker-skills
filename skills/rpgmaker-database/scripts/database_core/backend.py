"""复用正式数据库读写后端。"""
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('item_database_backend', Path(__file__).resolve().parents[1] / 'database.py')
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)


def integer(value, low=0, high=None):
    db.require(type(value) is int and value >= low and (high is None or value <= high), f'Expected integer {low}..{high}: {value!r}')
    return value


def number(value, low, high):
    db.require(type(value) in (int,float) and low <= value <= high, f'Expected number {low}..{high}: {value!r}')
    return value


def index(value, size):
    return integer(value,0,size-1)
