import html as _html
import math
import re
from datetime import datetime

import altair as alt
import pandas as pd
import polars as pl
import streamlit as st
import streamlit.components.v1 as components
from databricks.sdk import WorkspaceClient

from src.truproxy import TruProxy

w = WorkspaceClient()
WORKSPACE_URL = w.config.host
_workspace_id_match = re.search(r"adb-(\d+)\.", WORKSPACE_URL or "")
WORKSPACE_ID = _workspace_id_match.group(1) if _workspace_id_match else None


def _service_url(proxy_type: str, service_id: str | None) -> str | None:
    if not service_id:
        return None
    path = {
        "cluster": f"/compute/clusters/{service_id}",
        "pipeline": f"/pipelines/{service_id}",
        "warehouse": f"/sql/warehouses/{service_id}",
        "app": f"/apps-v2/app/{service_id}/overview",
    }.get(proxy_type)
    if not path:
        return None
    suffix = f"?o={WORKSPACE_ID}" if WORKSPACE_ID else ""
    return f"{WORKSPACE_URL}{path}{suffix}"

TIER = "PREMIUM"
REGION = "EU_WEST"
MAX_HISTORY = 120  # 10 min at 5 s intervals
PROXY_TYPES = ["cluster", "pipeline", "warehouse", "app"]
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
APP_CREAM = "#fce4ec"
APP_PINK = "#e91e63"
APP_PINK_PALETTE = [
    "#880e4f",  # very dark rose
    "#e91e63",  # strong pink
    "#ff5252",  # bright rose-red
    "#ff9800",  # orange contrast
    "#8e24aa",  # vivid purple
    "#3949ab",  # indigo contrast
    "#00838f",  # teal contrast
]
PROXY_COLOR = {
    "cluster": CLUSTER_BLUE,
    "pipeline": PIPELINE_GREEN,
    "warehouse": WAREHOUSE_ORANGE,
    "app": APP_PINK,
}
PROXY_TOTAL_COLOR = {
    "cluster": CLUSTER_CREAM,
    "pipeline": PIPELINE_CREAM,
    "warehouse": WAREHOUSE_CREAM,
    "app": APP_CREAM,
}
PROXY_PALETTE = {
    "cluster": CLUSTER_BLUE_PALETTE,
    "pipeline": PIPELINE_GREEN_PALETTE,
    "warehouse": WAREHOUSE_ORANGE_PALETTE,
    "app": APP_PINK_PALETTE,
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
    /* Pulse animation for the latest-point markers in every chart.
       Uses filter (not transform) so the inline transform="translate(x,y)"
       Vega puts on each path stays intact and the dot keeps its position. */
    .vega-embed g[class*="mark-symbol"] path {
        animation: tp-pulse 1s ease-in-out infinite;
    }
    @keyframes tp-pulse {
        0%, 100% { filter: drop-shadow(0 0 0 rgba(255,255,255,0)); }
        50%      { filter: drop-shadow(0 0 6px rgba(255,255,255,0.65)); }
    }

    /* Tone down page titles (st.header) and chart titles (st.subheader). */
    .main [data-testid="stHeading"] h1,
    .main [data-testid="stHeading"] h2 {
        font-size: 1.5rem;
        font-weight: 600;
    }
    .main [data-testid="stHeading"] h3 {
        font-size: 1rem;
        font-weight: 500;
    }
    /* Keep resource-table links white like normal table text. */
    .main .stTable a,
    .main .stTable a:visited,
    .main .stTable a:hover,
    .main .stTable a:active,
    .main [data-testid="stTable"] a,
    .main [data-testid="stTable"] a:visited,
    .main [data-testid="stTable"] a:hover,
    .main [data-testid="stTable"] a:active,
    .main [data-testid="stTable"] [data-testid="stMarkdownContainer"] a,
    .main [data-testid="stTable"] [data-testid="stMarkdownContainer"] a:visited,
    .main [data-testid="stTable"] [data-testid="stMarkdownContainer"] a:hover,
    .main [data-testid="stTable"] [data-testid="stMarkdownContainer"] a:active {
        color: #E8E5F5 !important;
        -webkit-text-fill-color: #E8E5F5 !important;
        text-decoration: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "pat_token" not in st.session_state:
    st.session_state.pat_token = ""
if "pat_scopes" not in st.session_state:
    st.session_state.pat_scopes = ["clusters", "pipelines", "sql", "apps"]
if "history" not in st.session_state:
    st.session_state.history = []
if "resource_meta" not in st.session_state:
    st.session_state.resource_meta = {pt: {} for pt in PROXY_TYPES}
if "page" not in st.session_state:
    st.session_state.page = "Overview" if st.session_state.pat_token else "Settings"

PAGES = ["Settings", "Overview", "Clusters", "Pipelines", "Warehouses", "Apps"]

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

    SCOPE_OPTIONS = ["clusters", "pipelines", "sql", "apps"]
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
            st.session_state.resource_meta = {pt: {} for pt in PROXY_TYPES}
            st.success("Settings saved.")


# ---- Data fetch + history ----
def _line_chart(
    df: pd.DataFrame,
    value_cols: list[str],
    height: int = 300,
    color_scale: alt.Scale | None = None,
    legend_links: dict[str, str] | None = None,
) -> None:
    long = (
        df[value_cols]
        .fillna(0)
        .reset_index()
        .melt("timestamp", var_name="series", value_name="cost")
    )
    latest_points = (
        long.sort_values("timestamp").groupby("series", as_index=False).tail(1).copy()
    )

    color = alt.Color(
        "series:N",
        title=None,
        legend=None if legend_links is not None else alt.Legend(
            orient="bottom", direction="horizontal"
        ),
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
    pulse_rings = (
        alt.Chart(latest_points)
        .mark_point(filled=True, size=240, opacity=0.18)
        .encode(
            x="timestamp:T",
            y="cost:Q",
            color=color,
            tooltip=alt.value(None),
        )
    )
    pulse_core = (
        alt.Chart(latest_points)
        .mark_point(filled=True, size=70, opacity=0.95)
        .encode(
            x="timestamp:T",
            y="cost:Q",
            color=color,
            tooltip=alt.value(None),
        )
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

    chart = alt.layer(lines, pulse_rings, pulse_core, selectors, points, hover).properties(
        height=height
    )
    st.altair_chart(chart, use_container_width=True)

    if legend_links is not None:
        _render_legend_links(value_cols, color_scale, legend_links)


def _render_legend_links(
    series: list[str],
    color_scale: alt.Scale | None,
    legend_links: dict[str, str],
) -> None:
    palette: list[str] = []
    if color_scale is not None:
        try:
            palette = list(color_scale.range)
        except AttributeError:
            palette = []

    def _color_for(idx: int) -> str:
        return palette[idx % len(palette)] if palette else "#888888"

    items = []
    for idx, name in enumerate(series):
        color = _color_for(idx)
        safe_name = _html.escape(str(name))
        swatch = (
            f'<span class="tp-swatch" data-series-idx="{idx}" '
            f'style="display:inline-block;width:11px;height:11px;'
            f'background:{color};border-radius:3px;flex-shrink:0;'
            f'cursor:default;"></span>'
        )
        url = legend_links.get(name)
        if url:
            text = (
                f'<a href="{_html.escape(url)}" target="_blank" rel="noopener noreferrer" '
                f'style="text-decoration:none;color:#E8E5F5;">{safe_name}</a>'
            )
        else:
            text = f'<span style="color:#E8E5F5;">{safe_name}</span>'
        items.append(
            f'<span class="tp-legend-item" '
            f'style="display:inline-flex;align-items:center;gap:6px;'
            f'margin:0 14px 6px 0;">{swatch}{text}</span>'
        )

    rows = max(1, math.ceil(len(items) / 4))
    height = 30 * rows + 20

    components.html(
        f"""
        <div id=\"tp-legend\" style=\"display:flex;flex-wrap:wrap;justify-content:center;
            font-size:0.85rem;color:#E8E5F5;\">{''.join(items)}</div>
        <script>
        (function() {{
            const parentDoc = window.parent.document;
            const myFrame = window.frameElement;

            try {{
                const parentFont = window.parent
                    .getComputedStyle(parentDoc.body).fontFamily;
                if (parentFont) document.body.style.fontFamily = parentFont;
                document.body.style.margin = '0';
            }} catch (e) {{}}

            function findChart() {{
                if (!myFrame) return null;
                const charts = parentDoc.querySelectorAll('.vega-embed');
                if (!charts.length) return null;
                const myTop = myFrame.getBoundingClientRect().top;
                let target = null;
                for (const c of charts) {{
                    const r = c.getBoundingClientRect();
                    if (r.bottom <= myTop + 10) target = c;
                }}
                return target;
            }}

            function lineMarks(chart) {{
                if (!chart) return [];
                return chart.querySelectorAll(
                    'g.mark-line path, g[class*="mark-line"] path'
                );
            }}
            function pointMarks(chart) {{
                if (!chart) return [];
                return chart.querySelectorAll(
                    'g.mark-symbol path, g[class*="mark-symbol"] path'
                );
            }}

            const allSwatches = Array.from(document.querySelectorAll('.tp-swatch'));
            allSwatches.forEach(sw => {{
                sw.style.transition = 'opacity 0.15s';
            }});

            function dim(idx) {{
                allSwatches.forEach((sw, i) => {{
                    sw.style.opacity = (i === idx ? '1' : '0.5');
                }});
                const chart = findChart();
                if (!chart) return;
                lineMarks(chart).forEach((p, i) => {{
                    p.style.transition = 'opacity 0.15s';
                    p.style.opacity = (i === idx ? '1' : '0.12');
                }});
                pointMarks(chart).forEach((p) => {{
                    p.style.transition = 'opacity 0.15s';
                    p.style.opacity = '0.15';
                }});
            }}
            function clear() {{
                allSwatches.forEach(sw => {{ sw.style.opacity = ''; }});
                const chart = findChart();
                if (!chart) return;
                lineMarks(chart).forEach(p => {{ p.style.opacity = ''; }});
                pointMarks(chart).forEach(p => {{ p.style.opacity = ''; }});
            }}

            allSwatches.forEach(sw => {{
                const idx = parseInt(sw.dataset.seriesIdx, 10);
                sw.addEventListener('mouseenter', () => dim(idx));
                sw.addEventListener('mouseleave', clear);
            }});
        }})();
        </script>
        """,
        height=height,
    )


def _page_overview(hist: pd.DataFrame) -> None:
    st.header("Overview")

    st.subheader("Total Cost ($/hr)")
    if "Total" in hist.columns:
        total_scale = alt.Scale(domain=["Total"], range=[TOTAL_GRAY])
        _line_chart(hist, ["Total"], color_scale=total_scale, legend_links={})
    else:
        st.info("Waiting for data…")

    st.subheader("Cost by Proxy Type ($/hr)")
    type_cols = [pt.capitalize() for pt in PROXY_TYPES if pt.capitalize() in hist.columns]
    if type_cols:
        type_color_scale = alt.Scale(
            domain=["Cluster", "Pipeline", "Warehouse", "App"],
            range=[CLUSTER_BLUE, PIPELINE_GREEN, WAREHOUSE_ORANGE, APP_PINK],
        )
        _line_chart(hist, type_cols, color_scale=type_color_scale, legend_links={})
    else:
        st.info("Waiting for data…")


def _resource_table(
    pt: str,
    renamed: pd.DataFrame,
    meta_map: dict[str, dict],
) -> None:
    def _format_state(state: object) -> str:
        raw = _html.escape(str(state or "").strip())
        normalized = raw.lower()
        if not raw:
            return ":gray-badge[UNKNOWN]"
        if normalized in {"running", "active", "online"}:
            return f":green-badge[{raw}]"
        if normalized in {"pending", "starting", "provisioning", "queued"}:
            return f":orange-badge[{raw}]"
        if normalized in {"stopped", "terminated", "offline", "failed", "error"}:
            return f":red-badge[{raw}]"
        return f":blue-badge[{raw}]"

    def _format_creator(creator: object) -> str:
        # Prevent browser email autolinking while preserving visible address.
        return _html.escape(str(creator or "").strip()).replace("@", "&#64;")

    names = list(renamed.columns)
    if not names:
        return
    latest = renamed.ffill().iloc[-1] if len(renamed) else pd.Series(dtype=float)
    ordered = sorted(
        names,
        key=lambda n: float(latest.get(n, 0.0) or 0.0),
        reverse=True,
    )

    rows = []
    for name in ordered:
        meta = meta_map.get(name, {})
        url = _service_url(pt, meta.get("service_id"))
        safe_name = _html.escape(str(name))
        if url:
            name_cell = f"[{safe_name}]({_html.escape(url)})"
        else:
            name_cell = safe_name
        rows.append(
            {
                "Resource Name": name_cell,
                "State": _format_state(meta.get("state", "")),
                "Creator": _format_creator(meta.get("creator", "")),
            }
        )
    table_df = pd.DataFrame(rows, columns=["Resource Name", "State", "Creator"])
    st.table(table_df, border="horizontal", hide_index=True)


def _page_proxy(pt: str, hist: pd.DataFrame) -> None:
    label = pt.capitalize()
    st.header(f"{label}s")

    total_color = PROXY_TOTAL_COLOR.get(pt)
    total_scale = (
        alt.Scale(domain=[label], range=[total_color]) if total_color else None
    )

    st.subheader(f"{label} Total Cost ($/hr)")
    if label in hist.columns:
        _line_chart(hist, [label], color_scale=total_scale, legend_links={})
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
        meta_map = st.session_state.resource_meta.get(pt, {})
        legend_links = {
            name: url
            for name in renamed.columns
            if (url := _service_url(pt, meta_map.get(name, {}).get("service_id")))
        }
        _line_chart(
            renamed,
            list(renamed.columns),
            color_scale=resource_scale,
            legend_links=legend_links,
        )
        _resource_table(pt, renamed, meta_map)
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
        with st.spinner("Loading latest costs..."):
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
        meta_map = st.session_state.resource_meta.setdefault(pt, {})
        names = sub["name"].to_list()
        service_ids = sub["service_id"].to_list()
        states = sub["state"].to_list()
        # The compiled truproxy-core binary doesn't currently emit creator;
        # fall back to empty strings until that's added.
        creators = (
            sub["creator"].to_list() if "creator" in sub.columns else [""] * len(names)
        )
        for name, service_id, state, creator in zip(names, service_ids, states, creators):
            cost = float(sub.filter(pl.col("name") == name)["total_cost"].sum())
            row[f"{pt}:{name}"] = cost
            meta_map[name] = {
                "state": state or "",
                "creator": creator or "",
                "service_id": service_id,
            }

    st.session_state.history.append(row)
    if len(st.session_state.history) > MAX_HISTORY:
        st.session_state.history = st.session_state.history[-MAX_HISTORY:]

    hist = pd.DataFrame(st.session_state.history).set_index("timestamp")

    # Prune meta entries whose names have fallen out of the history window.
    for pt in PROXY_TYPES:
        active_names = {
            c.split(":", 1)[1] for c in hist.columns if c.startswith(f"{pt}:")
        }
        meta_map = st.session_state.resource_meta.get(pt, {})
        for stale in [n for n in meta_map if n not in active_names]:
            meta_map.pop(stale, None)

    if page == "Overview":
        _page_overview(hist)
    elif page == "Clusters":
        _page_proxy("cluster", hist)
    elif page == "Pipelines":
        _page_proxy("pipeline", hist)
    elif page == "Warehouses":
        _page_proxy("warehouse", hist)
    elif page == "Apps":
        _page_proxy("app", hist)

    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
    st.caption(f"Last updated {now.strftime('%H:%M:%S')} · refreshes every 5 s")

if page == "Settings":
    _page_settings()
else:
    dashboard(page)