"""
dashboard.py -- Streamlit dashboard for Slay the Spire run analytics

Usage:
    streamlit run dashboard.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = Path(os.getenv("DB_PATH", "sts.db"))

st.set_page_config(page_title="STS Analytics", layout="wide")


@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


conn = get_conn()

st.title("Slay the Spire — Run Analytics")

# ── Win rate over time ────────────────────────────────────────────────────────

st.header("Win rate over time")

WINDOW = 20

df = pd.read_sql("""
    SELECT local_time, victory, ascension_level
    FROM runs
    WHERE local_time IS NOT NULL
    ORDER BY local_time ASC
""", conn)

df["run_number"] = range(1, len(df) + 1)
df["date"] = pd.to_datetime(df["local_time"].str[:8], format="%Y%m%d")
df["cumul_wr"] = df["victory"].expanding().mean() * 100
df["rolling_wr"] = df["victory"].rolling(WINDOW).mean() * 100

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["run_number"],
    y=df["cumul_wr"],
    name="Cumulative win rate",
    line=dict(color="#4e79a7", width=2),
    hovertemplate="Run %{x}<br>Cumulative WR: %{y:.1f}%<extra></extra>",
))

fig.add_trace(go.Scatter(
    x=df["run_number"],
    y=df["rolling_wr"],
    name=f"Rolling win rate (last {WINDOW})",
    line=dict(color="#f28e2b", width=2, dash="dash"),
    hovertemplate="Run %{x}<br>Rolling WR: %{y:.1f}%<extra></extra>",
))

# Mark wins as dots
wins = df[df["victory"] == 1]
fig.add_trace(go.Scatter(
    x=wins["run_number"],
    y=[0] * len(wins),
    mode="markers",
    name="Win",
    marker=dict(color="#59a14f", size=8, symbol="triangle-up"),
    hovertemplate="Run %{x} — Win (A" + wins["ascension_level"].astype(str) + ")<extra></extra>",
))

fig.update_layout(
    xaxis_title="Run number",
    yaxis_title="Win rate (%)",
    yaxis=dict(range=[0, 100]),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    height=450,
)

st.plotly_chart(fig, use_container_width=True)

# Summary stats below the chart
total = len(df)
wins_n = df["victory"].sum()
overall_wr = wins_n / total * 100
recent_wr = df["rolling_wr"].iloc[-1]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total runs", total)
col2.metric("Wins", int(wins_n))
col3.metric("Overall win rate", f"{overall_wr:.1f}%")
col4.metric(f"Last {WINDOW} runs", f"{recent_wr:.1f}%" if pd.notna(recent_wr) else "n/a")
