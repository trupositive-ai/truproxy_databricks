from datetime import datetime

import pandas as pd
import polars as pl
import streamlit as st
from databricks.sdk import WorkspaceClient

from src.truproxy import TruProxy

w = WorkspaceClient()
WORKSPACE_URL = w.config.host

TIER = "PREMIUM"
REGION = "EU_WEST"
MAX_HISTORY = 120  # 10 min at 5 s intervals
PROXY_TYPES = ["cluster", "pipeline", "warehouse"]

st.set_page_config(page_title="TruProxy Cost Monitor", layout="wide")

if "pat_token" not in st.session_state:
    st.session_state.pat_token = ""
if "history" not in st.session_state:
    st.session_state.history = []

# ---- Sidebar navigation ----
with st.sidebar:
    st.title("TruProxy")
    page = st.radio(
        "Page",
        ["Overview", "Clusters", "Pipelines", "Warehouses", "Settings"],
        label_visibility="collapsed",
    )

# ---- Settings page ----
def _page_settings() -> None:
    st.header("Settings")
    with st.form("settings_form"):
        pat_token = st.text_input(
            "Personal Access Token",
            value=st.session_state.pat_token,
            type="password",
            placeholder="dapi…",
        )
        submitted = st.form_submit_button("Save")
        if submitted:
            st.session_state.pat_token = pat_token.strip()
            # Reset TruProxy so it reinitialises with the new token
            st.session_state.pop("tp", None)
            st.session_state.history = []
            st.success("Settings saved.")


# ---- Data fetch + history ----
def _page_overview(hist: pd.DataFrame) -> None:
    st.header("Overview")

    st.subheader("Total Cost ($/hr)")
    if "Total" in hist.columns:
        st.line_chart(hist[["Total"]], height=300)
    else:
        st.info("Waiting for data…")

    st.subheader("Cost by Proxy Type ($/hr)")
    type_cols = [pt.capitalize() for pt in PROXY_TYPES if pt.capitalize() in hist.columns]
    if type_cols:
        st.line_chart(hist[type_cols], height=300)
    else:
        st.info("Waiting for data…")


def _page_proxy(pt: str, hist: pd.DataFrame) -> None:
    label = pt.capitalize()
    st.header(f"{label}s")

    st.subheader(f"{label} Total Cost ($/hr)")
    if label in hist.columns:
        st.line_chart(hist[[label]], height=300)
    else:
        st.info("No data yet.")

    st.subheader(f"{label} Cost by Resource ($/hr)")
    name_cols = [c for c in hist.columns if c.startswith(f"{pt}:")]
    if name_cols:
        chart = hist[name_cols].copy()
        chart.columns = [c.split(":", 1)[1] for c in name_cols]
        st.line_chart(chart, height=300)
    else:
        st.info("No active resources.")


@st.fragment(run_every=5)
def dashboard(page: str) -> None:
    if not st.session_state.pat_token:
        st.warning("Configure your Personal Access Token in **Settings** to start monitoring.")
        return

    if "tp" not in st.session_state:
        st.session_state.tp = TruProxy(
            token=st.session_state.pat_token,
            workspace_url=WORKSPACE_URL,
        )

    try:
        df = st.session_state.tp.get(tier=TIER, region=REGION)
    except Exception as exc:
        st.error(f"Fetch error: {exc}")
        return

    now = datetime.now()

    row: dict = {"timestamp": now}
    row["Total"] = float(df["total_cost"].sum())
    for pt in PROXY_TYPES:
        sub = df.filter(pl.col("proxy_type") == pt)
        row[pt.capitalize()] = float(sub["total_cost"].sum()) if len(sub) else 0.0

    for pt in PROXY_TYPES:
        sub = df.filter(pl.col("proxy_type") == pt)
        for name in sub["name"].to_list():
            cost = float(sub.filter(pl.col("name") == name)["total_cost"].sum())
            row[f"{pt}:{name}"] = cost

    st.session_state.history.append(row)
    if len(st.session_state.history) > MAX_HISTORY:
        st.session_state.history = st.session_state.history[-MAX_HISTORY:]

    hist = pd.DataFrame(st.session_state.history).set_index("timestamp")

    if page == "Overview":
        _page_overview(hist)
    elif page == "Clusters":
        _page_proxy("cluster", hist)
    elif page == "Pipelines":
        _page_proxy("pipeline", hist)
    else:
        _page_proxy("warehouse", hist)

    st.caption(f"Last updated {now.strftime('%H:%M:%S')} · refreshes every 5 s")


if page == "Settings":
    _page_settings()
else:
    dashboard(page)
