from __future__ import annotations

import ast
import re

import pandas as pd 
import plotly.express as px 
import streamlit as st

from agent import run_query

st.set_page_config(
    page_title="LangChain SQL Agent",
    page_icon=">",
    layout="wide",
)


st.title("LangChain SQL Agent")

with st.sidebar:
    st.header("About")
    st.markdown(
        """
        **Database:** Chinook SQLite (artists, albums, tracks, sales)
        **Model:** kimi-k2.6 via [Orq.ai](https://orq.ai)
        """
    )
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

def _column_names_from_sql(sql: str | None, num_cols: int) -> list[str]:
    """Derive display column names from the SELECT list when results are bare tuples."""
    if not sql or num_cols < 1:
        return [f"col_{i+1}" for i in range(num_cols)]
    
    match = re.search(r"\bSELECT\b(.+?)\bFROM\b", sql, re.IGNORECASE | re.DOTALL)
    if not match:
        return [f"col_{i+1}" for i in range(num_cols)]

    select_part = match.group(1).strip()
    if select_part == "*":
        return [f"col_{i+1}" for i in range(num_cols)]

    parts: list[str] = []
    depth = 0
    buf: list[str] = []

    for char in select_part + ",":
        if char == "(":
            depth += 1
            buf.append(char)
        elif char == ")":
            depth = max(0, depth - 1)
            buf.append(char)
        elif char == "," and depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
                buf = []
        else:
            buf.append(char)

        names: list[str] = []
        for part in parts:
            alias = re.search(
                r"\bAS\s+(?:[`\"']?)([A-Za-z_][\w$]*)(?:[`\"']?)\s*$",
                part,
                re.IGNORECASE,
            )
            if alias:
                names.append(alias.group(1))
                continue

            token = part.strip().rstrip(",").split()[-1]
            token = token.strip("`\"'[]")
            names.append(token.split(".")[-1] if token else f"col{len(names) + 1}")

        if len(names) >= num_cols:
            return names[:num_cols]
        return names + [f"col {i+1}" for i in range(len(names), num_cols)]

def _parse_results(raw: str | None, sql: str | None = None) -> pd.DataFrame | None:
    """Parse raw SQL query results into a df."""
    if not raw or not raw.strip():
        return None

    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            rows = asr.literal_eval(text)
            if not rows:
                return None
            if isinstance(rows[0], dict):
                return pd.DataFrame(rows)
            if isinstance(rows[0], tuple):
                cols = _column_names_from_sql(sql, len(rows[0]))
                return pd.DataFrame(rows, cols)
        except (SyntaxError, ValueError):
            pass

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    
    header = re.split(r"\s*\|\s*", lines[0].strip("| "))
    data_rows = []
    for line in lines[2:]:
        if set(line.replace("|", "").strip()) <= {"-", ":"}:
            continue
        data_rows.append(re.split(r"\s*\|\s*", line.strip("| ")))

    if header and data_rows:
        width = len(header)
        normalized = [row[:width] + [""] * (width - len(row)) for row in data_rows]
        df = pd.DataFrame(normalized, columns=header)
        for col in df.columns:
            converted = pd.to_numeric(df[col], errors="coerce")
            if converted.notna().any():
                df[col] = converted
        return df

    return None