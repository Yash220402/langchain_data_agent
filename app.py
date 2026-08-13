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

