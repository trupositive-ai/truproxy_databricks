from datetime import datetime

import altair as alt
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
TOTAL_GRAY = "#e0e0e0"
CLUSTER_CREAM = "#cfe2f3"
PIPELINE_CREAM = "#d9ead3"
WAREHOUSE_CREAM = "#fce5cd"
CLUSTER_BLUE = "#2196f3"
CLUSTER_BLUE_PALETTE = [
    "#42a5f5",  # sky blue
    "#2962ff",  # electric blue
    "#00bcd4",  # bright cyan
    "#7986cb",  # periwinkle
    "#81d4fa",  # pale sky
    "#9575cd",  # light purple-blue
    "#4fc3f7",  # light azure
]
PIPELINE_GREEN = "#2ca02c"
PIPELINE_GREEN_PALETTE = [
    "#66bb6a",  # medium green
    "#00e676",  # bright green
    "#9ccc65",  # lime
    "#26a69a",  # teal-green
    "#aed581",  # light lime
    "#4db6ac",  # bright teal
    "#80cbc4",  # pale mint
]
WAREHOUSE_ORANGE = "#ff7f0e"
WAREHOUSE_ORANGE_PALETTE = [
    "#ff3d00",  # vivid vermillion (red-orange end)
    "#ff9800",  # pure bright orange
    "#ffc107",  # golden amber (yellow-orange end)
    "#ff7043",  # coral (pink-leaning)
    "#ffab40",  # light gold
    "#ffe082",  # pale cream-amber
    "#ffcc80",  # pale peach
]
PROXY_COLOR = {
    "cluster": CLUSTER_BLUE,
    "pipeline": PIPELINE_GREEN,
    "warehouse": WAREHOUSE_ORANGE,
}
PROXY_TOTAL_COLOR = {
    "cluster": CLUSTER_CREAM,
    "pipeline": PIPELINE_CREAM,
    "warehouse": WAREHOUSE_CREAM,
}
PROXY_PALETTE = {
    "cluster": CLUSTER_BLUE_PALETTE,
    "pipeline": PIPELINE_GREEN_PALETTE,
    "warehouse": WAREHOUSE_ORANGE_PALETTE,
}

st.set_page_config(page_title="TruProxy Cost Monitor", page_icon="💸", layout="wide")

# ---- Sidebar nav styling: left-aligned labels, no border, highlight only when selected ----
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
        padding: 0;
        margin: 0;
        min-height: 0;
        height: 0;
        position: relative;
    }
    section[data-testid="stSidebar"] [data-testid="stLogoSpacer"] {
        display: none;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {
        position: absolute;
        top: 1.25rem;
        right: 0.75rem;
        z-index: 10;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding-top: 1rem;
        margin-top: 0;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] h1 {
        padding-top: 0;
        padding-bottom: 1rem;
        margin-top: 0;
        margin-bottom: 0;
        border-bottom: 1px solid rgba(232, 229, 245, 0.15);
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] [data-testid="stHeading"] {
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
        justify-content: flex-start;
        text-align: left;
        border: none;
        box-shadow: none;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button p {
        text-align: left;
        width: 100%;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: transparent;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"]:hover,
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"]:focus:not(:active) {
        background-color: transparent;
        color: inherit;
        border: none;
        box-shadow: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "pat_token" not in st.session_state:
    st.session_state.pat_token = ""
if "pat_scopes" not in st.session_state:
    st.session_state.pat_scopes = ["clusters", "pipelines", "sql"]
if "history" not in st.session_state:
    st.session_state.history = []
if "page" not in st.session_state:
    st.session_state.page = "Overview" if st.session_state.pat_token else "Settings"

PAGES = ["Settings", "Overview", "Clusters", "Pipelines", "Warehouses"]

# ---- Sidebar navigation ----
with st.sidebar:
    st.title("TruProxy")
    for _nav in PAGES:
        if st.button(
            _nav,
            key=f"nav_{_nav}",
            use_container_width=True,
            type="primary" if st.session_state.page == _nav else "secondary",
        ):
            st.session_state.page = _nav
            st.rerun()

page = st.session_state.page


# ---- Settings page ----
def _page_settings() -> None:
    st.header("Settings")

    st.markdown(
        """
        ### Create a Databricks Personal Access Token

        1. In your Databricks workspace, click your **user avatar** (top-right) → **Settings**.
        2. Go to **Developer** → **Access tokens** → **Manage**.
        3. Click **Generate new token**, add a comment (e.g. `TruProxy`) and set a lifetime.
        4. Click **Generate** and copy the token (starts with `dapi…`) — it is shown only once.

        ### Required permissions

        Databricks PATs inherit the generating user's workspace permissions. Make sure you grant `read access` to the following resources:

        When creating the PAT, make sure to select **all** of the following
        API scopes so TruProxy can read every resource it monitors:
        """
    )

    SCOPE_OPTIONS = ["clusters", "pipelines", "sql"]
    pat_scopes = st.pills(
        "API scopes",
        options=SCOPE_OPTIONS,
        default=st.session_state.pat_scopes,
        selection_mode="multi",
        label_visibility="collapsed",
    )

    st.markdown("Paste the token below to start monitoring.")

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
            st.session_state.pat_scopes = pat_scopes or []
            # Reset TruProxy so it reinitialises with the new token
            st.session_state.pop("tp", None)
            st.session_state.history = []
            st.success("Settings saved.")


# ---- Data fetch + history ----
def _line_chart(
    df: pd.DataFrame,
    value_cols: list[str],
    height: int = 300,
    color_scale: alt.Scale | None = None,
) -> None:
    long = (
        df[value_cols]
        .reset_index()
        .melt("timestamp", var_name="series", value_name="cost")
    )

    color = alt.Color(
        "series:N",
        title=None,
        legend=alt.Legend(orient="bottom", direction="horizontal"),
    )
    if color_scale is not None:
        color = color.scale(color_scale)

    base = alt.Chart(long).encode(
        x=alt.X(
            "timestamp:T",
            title=None,
            axis=alt.Axis(format="%H:%M:%S", tickCount=6, labelOverlap=True),
        ),
        y=alt.Y("cost:Q", title="$/hr", axis=alt.Axis(format="$.2f")),
        color=color,
    )

    lines = base.mark_line()

    nearest = alt.selection_point(
        nearest=True,
        on="mouseover",
        fields=["timestamp"],
        empty=False,
    )

    selectors = (
        alt.Chart(long)
        .mark_rule(opacity=0)
        .encode(x="timestamp:T", tooltip=alt.value(None))
        .add_params(nearest)
    )

    points = lines.mark_point().encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        tooltip=alt.value(None),
    )

    hover = (
        alt.Chart(long)
        .mark_rule(color="gray")
        .encode(
            x="timestamp:T",
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time", format="%Y-%m-%d %H:%M:%S"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("cost:Q", title="$/hr", format=".4f"),
            ],
        )
        .transform_filter(nearest)
    )

    chart = alt.layer(lines, selectors, points, hover).properties(height=height)
    st.altair_chart(chart, use_container_width=True)


def _page_overview(hist: pd.DataFrame) -> None:
    st.header("Overview")

    st.subheader("Total Cost ($/hr)")
    if "Total" in hist.columns:
        total_scale = alt.Scale(domain=["Total"], range=[TOTAL_GRAY])
        _line_chart(hist, ["Total"], color_scale=total_scale)
    else:
        st.info("Waiting for data…")

    st.subheader("Cost by Proxy Type ($/hr)")
    type_cols = [pt.capitalize() for pt in PROXY_TYPES if pt.capitalize() in hist.columns]
    if type_cols:
        type_color_scale = alt.Scale(
            domain=["Cluster", "Pipeline", "Warehouse"],
            range=[CLUSTER_BLUE, PIPELINE_GREEN, WAREHOUSE_ORANGE],
        )
        _line_chart(hist, type_cols, color_scale=type_color_scale)
    else:
        st.info("Waiting for data…")


def _page_proxy(pt: str, hist: pd.DataFrame) -> None:
    label = pt.capitalize()
    st.header(f"{label}s")

    total_color = PROXY_TOTAL_COLOR.get(pt)
    total_scale = (
        alt.Scale(domain=[label], range=[total_color]) if total_color else None
    )

    st.subheader(f"{label} Total Cost ($/hr)")
    if label in hist.columns:
        _line_chart(hist, [label], color_scale=total_scale)
    else:
        st.info("No data yet.")

    st.subheader(f"{label} Cost by Resource ($/hr)")
    name_cols = [c for c in hist.columns if c.startswith(f"{pt}:")]
    if name_cols:
        renamed = hist[name_cols].copy()
        renamed.columns = [c.split(":", 1)[1] for c in name_cols]
        palette = PROXY_PALETTE.get(pt)
        resource_scale = (
            alt.Scale(domain=list(renamed.columns), range=palette) if palette else None
        )
        _line_chart(renamed, list(renamed.columns), color_scale=resource_scale)
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