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

def _build_model():
    """BUild and return the ChatOpenAI client"""
    api_key = os.getenv("ORQ_API_KEY")
    if not api_key:
        raise ValueError("ORQ_API_KEY is not set. Copy .env.example to .env and add your key")
    return ChatOpenAI(
        model="kimi-k2.6",
        openai_api_key=api_key,
        openai_api_base="https://api.orq.ai/v3/router",
        temperature=1,
        extra_body={"thinking": {"type": "disabled"}},
    )

def _build_tools(db: SQLDatabase, model: ChatOpenAI) -> list:
    """Build the LangChain SQL toolkit and replace the default query tool with the read only version."""
    toolkit = SQLDatabaseToolkit(db=db, llm=model)
    tools = toolkit.get_tools()
    for i, tool in enumerate(tools):
        if tool.name == "sql_db_query":
            tools[i] = ReadOnlyQuerySQLDatabaseTool(db=db)
    return tools

def ReadOnlyQuerySQLDatabaseTool(db: SQLDatabase):
    """SQL query tool that rejects non-SELECT statements."""
    
    def _run(self, query:str, run_manager=None) -> str:
        safe_query = _validate_read_only(query)
        return self.db.run_no_throw(safe_query, include_columns=True)

def _create_agent():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH.resolve()}")
    model = _build_model()
    tools = _build_tools(db, model)
