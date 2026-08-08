import os
import re
from pathlib import Path
from typing import Literal

DB_PATH = Path(__file__).parent / "chinook.db"

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|"
    r"GRANT|REVOKE|ATTACH|DETACH|MERGE|CALL|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)
READ_ONLY_SQL = re.compile(r"^\s*(SELECT|WITH|PRAGMA|EXPLAIN)\b", re.IGNORECASE | re.DOTALL)

def _validate_read_only(query:str) -> str:
    cleaned = query.strip().rstrip(";")
    if FORBIDDEN_SQL.search(cleaned):
        raise ValueError("Only read only SELECT queries are allowed.")
    if not READ_ONLY_SQL.match(cleaned):
        raise ValueError('Only read only SELECT queries are allowed.')
    return cleaned