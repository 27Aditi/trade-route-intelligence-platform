import dash
from dash import dcc, html, dash_table, Input, Output, State, no_update, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import base64, io

from modules.risk_engine import (
    calculate_route_risk, calculate_country_risk,
    find_single_points_of_failure, calculate_resilience_score
)
from modules.graph_engine import build_graph, get_critical_nodes, find_alternatives
from modules.map_view import build_full_map, TRANSPORT_COLORS
from modules.ingestion import load_trade_data, validate_columns, get_summary

ACCENT = "#6d5efc"
ACCENT2 = "#22d3ee"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"
DANGER = "#ef4444"
TEXT_DIM = "#a3a5b8"
MUTED = "#6b6d82"

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.BOOTSTRAP]
)
app.title = "TradeRoute Intelligence Platform"
server = app.server


def fmt_usd(v):
    v = float(v)
    if v >= 1e9:
        return f"${v/1e9:.2f}B"
    if v >= 1e6:
        return f"${v/1e6:.1f}M"
    if v >= 1e3:
        return f"${v/1e3:.1f}K"
    return f"${v:,.0f}"


def risk_color(score):
    s = float(score)
    if s < 3:
        return SUCCESS
    if s < 6:
        return WARNING
    return DANGER


def risk_label(score):
    s = float(score)
    if s < 3:
        return "LOW"
    if s < 6:
        return "MEDIUM"
    return "HIGH"


def badge(text, color):
    return html.Span(text, className="badge-pill", style={
        "background": color + "22", "color": color, "borderColor": color + "55"
    })


def info_row(label, value, color=None):
    return html.Div([
        html.Span(label, className="info-label"),
        html.Span(str(value), className="info-value",
                  style={"color": color} if color else {})
    ], className="info-row")


def kpi_card(label, value, sub="", accent=ACCENT):
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(str(value), className="kpi-value", style={"color": accent}),
        html.Div(sub, className="kpi-sub")
    ], className="kpi-card", style={"--accent-color": accent})


def empty_card(title, icon, message):
    return html.Div([
        html.Div([html.I(className=f"bi {icon} me-2"), title], className="card-title",
                  style={"color": ACCENT}),
        html.P(message, className="empty-state")
    ], className="card")


def parse_upload(contents):
    _, b64 = contents.split(",", 1)
    return pd.read_csv(io.StringIO(base64.b64decode(b64).decode()))


def enrich_dataframe(df):
    rng = np.random.default_rng(42)
    risk_cols = ["inform_risk", "conflict_score", "hazard_score",
                 "vulnerability_score", "coping_capacity_score"]
    for prefix in ["from_", "to_"]:
        for c in risk_cols:
            col = prefix + c
            if col not in df.columns:
                df[col] = rng.uniform(1, 8, len(df))
    df = calculate_route_risk(df)
    return df


def simulate_disruption(df, country):
    df2 = df.copy()
    if "risk_level" in df2.columns:
        df2["risk_level"] = df2["risk_level"].astype(str)

    mask = (df2["from_country"] == country) | (df2["to_country"] == country)
    affected = df2[mask].copy()
    unaffected = df2[~mask].copy()

    total_loss = float(affected["trade_value_usd"].sum())
    products = affected["product_category"].unique().tolist()

    all_countries = set(df2["from_country"].tolist() + df2["to_country"].tolist())
    remaining = all_countries - {country}
    remaining_routes = unaffected[
        unaffected["from_country"].isin(remaining) & unaffected["to_country"].isin(remaining)
    ]
    connected = set(remaining_routes["from_country"].tolist() + remaining_routes["to_country"].tolist())
    isolated = remaining - connected
    network_broken = len(isolated) > 0

    avg_dep = float(affected["dependency_percent"].mean()) if len(affected) else 0
    top_routes = affected.nlargest(8, "trade_value_usd")[
        ["from_country", "to_country", "product_category", "trade_value_usd", "transport_mode", "transit_days"]
    ].to_dict("records")
    prod_breakdown = (affected.groupby("product_category")["trade_value_usd"]
                      .sum().sort_values(ascending=False).head(6))

    return {
        "country": country,
        "total_loss": total_loss,
        "routes_affected": int(mask.sum()),
        "products": products,
        "network_broken": network_broken,
        "isolated_count": len(isolated),
        "avg_dependency": avg_dep,
        "top_routes": top_routes,
        "prod_breakdown": prod_breakdown
    }


def topbar():
    return html.Div([
        html.Div([
            html.Div("◈", className="brand-mark"),
            html.Div([
                html.H1("TradeRoute Intelligence Platform", className="brand-title"),
                html.P("Global Supply Chain · Risk Intelligence · Disruption Simulation",
                       className="brand-subtitle")
            ])
        ], className="brand"),
        html.Div([
            html.Div([
                html.Div(className="legend-dot", style={"background": col}),
                html.Span(mode)
            ], className="legend-item")
            for mode, col in TRANSPORT_COLORS.items()
        ], className="legend-strip")
    ], className="topbar")


def control_row():
    return html.Div([
        dcc.Upload(
            id="upload-data",
            children=html.Div([
                html.I(className="bi bi-cloud-arrow-up-fill", style={"color": ACCENT, "fontSize": "18px"}),
                html.Span("Upload Trade CSV", className="upload-label"),
                html.Span("drag & drop or click", className="upload-hint")
            ], style={"display": "flex", "alignItems": "center", "gap": "10px"}),
            className="upload-zone",
            multiple=False
        ),
        html.Span("OR", className="divider-or"),
        html.Button([
            html.I(className="bi bi-play-fill me-2"), "Load Sample Dataset"
        ], id="sample-btn", n_clicks=0, className="btn-sample"),
        html.Div(id="upload-status", className="upload-status")
    ], className="control-row")


def kpi_section():
    return html.Div(
        id="kpi-row",
        className="kpi-grid section-pad",
        children=[
            kpi_card("Total Trade Value", "—", "Upload data to begin", ACCENT),
            kpi_card("Active Countries", "—", "", ACCENT2),
            kpi_card("Trade Routes", "—", "", WARNING),
            kpi_card("Network Resilience", "—", "0 (fragile) → 10 (robust)", SUCCESS),
        ]
    )


def map_panel():
    return html.Div([
        html.Div([
            dcc.Loading(
                dcc.Graph(
                    id="trade-map",
                    style={"height": "560px"},
                    config={"scrollZoom": True, "displayModeBar": True,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
                            "displaylogo": False},
                    figure=go.Figure(layout=go.Layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False,
                                 showland=True, landcolor="#12131c",
                                 showocean=True, oceancolor="#0a0b12",
                                 showcountries=True, countrycolor="#1d1e2c",
                                 projection_type="natural earth"),
                        margin=dict(l=0, r=0, t=0, b=0),
                        annotations=[dict(
                            text="Upload a trade CSV or load the sample dataset to begin",
                            x=0.5, y=0.5, xref="paper", yref="paper",
                            showarrow=False, font=dict(color=MUTED, size=13))]
                    ))
                ),
                type="circle", color=ACCENT
            )
        ], className="card", style={"flex": "1", "minWidth": 0, "padding": "10px"}),

        html.Div([
            html.Div(
                id="hover-panel",
                children=empty_card("Node Profile", "bi-geo-alt-fill",
                                     "Hover over a country node to inspect its trade profile."),
                style={"marginBottom": "14px"}
            ),
            html.Div(
                id="disruption-side",
                children=empty_card("Quick Disruption View", "bi-lightning-charge-fill",
                                     "Click any node on the map to simulate its failure."),
            ),
        ], style={"width": "300px", "flexShrink": 0})
    ], style={"display": "flex", "gap": "16px", "alignItems": "flex-start"}, className="section-pad")


def disruption_panel():
    return html.Div([
        html.Div(id="disruption-kpis",
                 children=empty_card("Disruption Impact", "bi-lightning-charge-fill",
                                      "Select a country on the Trade Map tab to run a disruption simulation.")),
        html.Div(id="disruption-detail", style={"marginTop": "16px"})
    ], className="section-pad")


def network_panel():
    return html.Div(
        id="network-panel",
        className="section-pad",
        children=empty_card("Network Resilience", "bi-diagram-3-fill",
                             "Load a dataset to analyse critical nodes and single points of failure.")
    )


app.layout = html.Div([
    dcc.Store(id="store-df"),
    topbar(),
    control_row(),
    kpi_section(),
    dcc.Tabs(
        id="tabs", value="tab-map", className="tab-bar",
        children=[
            dcc.Tab(label="Trade Map", value="tab-map"),
            dcc.Tab(label="Disruption Lab", value="tab-disruption"),
            dcc.Tab(label="Network Resilience", value="tab-network"),
        ]
    ),
    html.Div(id="panel-map", children=map_panel()),
    html.Div(id="panel-disruption", children=disruption_panel(), style={"display": "none"}),
    html.Div(id="panel-network", children=network_panel(), style={"display": "none"}),
    html.P("Bring your own trade dataset or explore the bundled sample — everything runs client-side per session.",
           className="footer-note")
], className="app-shell")


@app.callback(
    Output("panel-map", "style"),
    Output("panel-disruption", "style"),
    Output("panel-network", "style"),
    Input("tabs", "value")
)
def switch_tabs(tab):
    show, hide = {"display": "block"}, {"display": "none"}
    return (
        show if tab == "tab-map" else hide,
        show if tab == "tab-disruption" else hide,
        show if tab == "tab-network" else hide
    )


def build_network_panel(df):
    G = build_graph(df)
    critical_df = get_critical_nodes(G)
    spof = find_single_points_of_failure(df)
    resilience = calculate_resilience_score(df)

    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=resilience,
        number={"font": {"color": risk_color(10 - resilience), "size": 40}},
        gauge={
            "axis": {"range": [0, 10], "tickcolor": MUTED, "tickfont": {"color": MUTED, "size": 10}},
            "bar": {"color": ACCENT},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 4], "color": "rgba(239,68,68,0.18)"},
                {"range": [4, 7], "color": "rgba(245,158,11,0.18)"},
                {"range": [7, 10], "color": "rgba(34,197,94,0.18)"}
            ]
        }
    ))
    gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", height=220,
        margin=dict(l=20, r=20, t=30, b=10),
        font=dict(color="#e8e9f3", family="'Inter','Segoe UI',sans-serif")
    )

    spof_children = [
        html.Div([
            html.Div([
                html.Span(row["country"], style={"fontWeight": "800", "color": DANGER}),
                badge(f"{row['avg_dependency']}% dependency", DANGER)
            ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "6px"}),
            html.Div(f"Exposure: {fmt_usd(row['total_exposure_usd'])} · "
                     f"Products: {', '.join(row['products_at_risk'][:3])}",
                     style={"fontSize": "11.5px", "color": TEXT_DIM})
        ], className="node-list-row", style={"flexDirection": "column", "alignItems": "stretch"})
        for row in spof
    ] or [html.P("No single points of failure detected above the 60% dependency threshold.",
                  className="empty-state")]

    node_rows = []
    for i, row in enumerate(critical_df.head(12).itertuples()):
        node_rows.append(html.Div([
            html.Div(f"{i+1}", className="rank-badge"),
            html.Div([
                html.Div(row.country, style={"fontWeight": "700", "fontSize": "13px"}),
                html.Div(f"Betweenness {row.betweenness_score} · Degree {row.degree_score}",
                         style={"fontSize": "10.5px", "color": MUTED})
            ], style={"flex": "1"}),
            badge(f"{row.criticality_score:.3f}", ACCENT2)
        ], className="node-list-row"))

    return html.Div([
        html.Div([
            html.Div([
                html.Div([html.I(className="bi bi-shield-check me-2"), "Network Resilience Score"],
                         className="card-title", style={"color": ACCENT}),
                dcc.Graph(figure=gauge, config={"displayModeBar": False}),
                html.P("Derived from average route risk, high-risk route count, and detected "
                       "single points of failure. Higher is more resilient.",
                       className="empty-state", style={"marginTop": "4px"})
            ], className="card", style={"marginBottom": "16px"}),

            html.Div([
                html.Div([html.I(className="bi bi-exclamation-triangle-fill me-2"), "Single Points of Failure"],
                         className="card-title", style={"color": DANGER}),
                *spof_children
            ], className="card")
        ], style={"flex": "1", "minWidth": "300px"}),

        html.Div([
            html.Div([html.I(className="bi bi-diagram-3-fill me-2"), "Most Critical Trade Nodes"],
                     className="card-title", style={"color": ACCENT}),
            html.P("Ranked by network betweenness and connectivity — the countries whose failure "
                   "would most disrupt global trade flow.", className="empty-state",
                   style={"marginBottom": "14px"}),
            *node_rows
        ], className="card", style={"flex": "1.4", "minWidth": "340px"})
    ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"})


@app.callback(
    Output("store-df", "data"),
    Output("trade-map", "figure"),
    Output("upload-status", "children"),
    Output("kpi-row", "children"),
    Output("network-panel", "children"),
    Output("hover-panel", "children"),
    Output("disruption-side", "children"),
    Output("disruption-kpis", "children"),
    Output("disruption-detail", "children"),
    Output("tabs", "value"),
    Input("upload-data", "contents"),
    Input("sample-btn", "n_clicks"),
    State("upload-data", "filename"),
    prevent_initial_call=True
)
def load_dataset(contents, n_clicks, filename):
    trigger = callback_context.triggered_id
    source_name = filename or "sample_trade.csv"

    try:
        if trigger == "sample-btn":
            df = load_trade_data()
            source_name = "sample_trade.csv (bundled sample)"
        elif contents:
            df = parse_upload(contents)
        else:
            return (no_update,) * 10

        ok, missing = validate_columns(df)
        if not ok:
            status = [
                html.I(className="bi bi-x-circle-fill me-2", style={"color": DANGER}),
                html.Span(f"Missing required columns: {', '.join(missing)}", style={"color": DANGER})
            ]
            return no_update, no_update, status, no_update, no_update, no_update, no_update, no_update, no_update, no_update

        df = enrich_dataframe(df)
        country_risk_df = calculate_country_risk(df)
        fig = build_full_map(df, country_risk_df)

        summary = get_summary(df)
        resilience = calculate_resilience_score(df)

        kpis = [
            kpi_card("Total Trade Value", fmt_usd(summary["total_trade_value"]),
                     f"{summary['num_routes']} trade routes", ACCENT),
            kpi_card("Active Countries", summary["num_countries"],
                     f"{summary['num_products']} product categories", ACCENT2),
            kpi_card("Trade Routes", summary["num_routes"], source_name, WARNING),
            kpi_card("Network Resilience", f"{resilience}/10",
                     risk_label(10 - resilience) + " fragility", risk_color(10 - resilience)),
        ]

        status = [
            html.I(className="bi bi-check-circle-fill me-2", style={"color": SUCCESS}),
            html.Span(f"{source_name} · {len(df)} routes · "
                      f"{summary['num_countries']} countries", style={"color": TEXT_DIM})
        ]

        network_children = build_network_panel(df)
        hover_reset = empty_card("Node Profile", "bi-geo-alt-fill",
                                  "Hover over a country node to inspect its trade profile.")
        disruption_side_reset = empty_card("Quick Disruption View", "bi-lightning-charge-fill",
                                            "Click any node on the map to simulate its failure.")
        disruption_kpis_reset = empty_card("Disruption Impact", "bi-lightning-charge-fill",
                                            "Select a country on the Trade Map tab to run a disruption simulation.")

        return (
            df.to_json(date_format="iso", orient="split"), fig, status, kpis,
            network_children, hover_reset, disruption_side_reset, disruption_kpis_reset,
            html.Div(), "tab-map"
        )

    except Exception as e:
        status = [
            html.I(className="bi bi-x-circle-fill me-2", style={"color": DANGER}),
            html.Span(str(e), style={"color": DANGER, "fontSize": "12.5px"})
        ]
        return no_update, no_update, status, no_update, no_update, no_update, no_update, no_update, no_update, no_update


@app.callback(
    Output("hover-panel", "children"),
    Input("trade-map", "hoverData"),
    State("store-df", "data"),
    prevent_initial_call=True
)
def on_hover(hoverData, df_json):
    if not hoverData or not df_json:
        return no_update
    try:
        pt = hoverData["points"][0]
        if "customdata" not in pt:
            return no_update

        country = pt["customdata"]
        df = pd.read_json(io.StringIO(df_json), orient="split")
        if "risk_level" in df.columns:
            df["risk_level"] = df["risk_level"].astype(str)

        out_r = df[df["from_country"] == country]
        in_r = df[df["to_country"] == country]
        total = float(out_r["trade_value_usd"].sum() + in_r["trade_value_usd"].sum())
        products = list(pd.concat([out_r["product_category"], in_r["product_category"]]).unique())
        modes = list(pd.concat([out_r["transport_mode"], in_r["transport_mode"]]).unique())
        combined = df[(df["from_country"] == country) | (df["to_country"] == country)]
        avg_risk = float(combined["route_risk_score"].mean()) if len(combined) else 0
        avg_dep = float(combined["dependency_percent"].mean()) if len(combined) else 0
        iso3 = df[df["from_country"] == country]["from_iso3"].iloc[0] if len(out_r) else "—"
        rc = risk_color(avg_risk)

        return html.Div([
            html.Div([html.I(className="bi bi-geo-alt-fill me-2"), "Node Profile"],
                      className="card-title", style={"color": ACCENT}),
            html.Div([
                html.Span(country, style={"fontSize": "16px", "fontWeight": "900"}),
                html.Span(f"  {iso3}", style={"fontSize": "10px", "color": MUTED, "letterSpacing": "0.1em"})
            ], style={"marginBottom": "12px"}),
            info_row("Total Trade Volume", fmt_usd(total), ACCENT2),
            info_row("Outbound Routes", len(out_r)),
            info_row("Inbound Routes", len(in_r)),
            info_row("Avg Dependency", f"{avg_dep:.1f}%"),
            html.Div([
                html.Span("Route Risk", className="info-label"),
                badge(f"{risk_label(avg_risk)} {avg_risk:.2f}", rc)
            ], className="info-row"),
            html.Div([
                html.Span(m, className="chip", style={
                    "background": TRANSPORT_COLORS.get(m, "#555") + "22",
                    "color": TRANSPORT_COLORS.get(m, "#aaa")
                }) for m in modes
            ], style={"marginBottom": "8px"}),
            html.Div([
                html.Span(p, className="chip", style={"background": ACCENT + "18", "color": "#c9c3ff"})
                for p in products[:6]
            ])
        ], className="card")

    except Exception:
        return no_update


@app.callback(
    Output("disruption-side", "children"),
    Output("disruption-kpis", "children"),
    Output("disruption-detail", "children"),
    Output("tabs", "value", allow_duplicate=True),
    Input("trade-map", "clickData"),
    State("store-df", "data"),
    prevent_initial_call=True
)
def on_click(clickData, df_json):
    if not clickData or not df_json:
        return no_update, no_update, no_update, no_update
    try:
        pt = clickData["points"][0]
        if "customdata" not in pt:
            return no_update, no_update, no_update, no_update

        country = pt["customdata"]
        df = pd.read_json(io.StringIO(df_json), orient="split")
        if "risk_level" in df.columns:
            df["risk_level"] = df["risk_level"].astype(str)

        R = simulate_disruption(df, country)
        tv_fmt = fmt_usd(R["total_loss"])
        broken_color = DANGER if R["network_broken"] else SUCCESS
        broken_txt = f"{R['isolated_count']} isolated" if R["network_broken"] else "Intact"

        side = html.Div([
            html.Div([html.I(className="bi bi-lightning-charge-fill me-2"), "Quick Disruption View"],
                      className="card-title", style={"color": WARNING}),
            html.Div([
                html.Span("Simulating ", style={"color": MUTED, "fontSize": "11px"}),
                html.Span(country, style={"color": WARNING, "fontWeight": "800"})
            ], style={"marginBottom": "10px"}),
            info_row("Trade at Risk", tv_fmt, ACCENT),
            info_row("Routes Cut", R["routes_affected"], DANGER),
            info_row("Products Hit", len(R["products"]), WARNING),
            html.Div([
                html.Span("Network", className="info-label"),
                badge(broken_txt, broken_color)
            ], className="info-row", style={"border": "none"})
        ], className="card")

        kpis = html.Div([
            html.Div([html.I(className="bi bi-lightning-charge-fill me-2"),
                      f"Simulating failure of {country}"],
                     className="card-title", style={"color": WARNING}),
            html.Div([
                kpi_card("Trade at Risk", tv_fmt, "Immediate exposure", ACCENT),
                kpi_card("Routes Disrupted", R["routes_affected"], "Direct connections", DANGER),
                kpi_card("Products Affected", len(R["products"]),
                         ", ".join(R["products"][:2]) + ("…" if len(R["products"]) > 2 else ""), ACCENT2),
                kpi_card("Avg Dependency", f"{R['avg_dependency']:.1f}%", "On disrupted country", WARNING),
                kpi_card("Network Status", broken_txt, "Post-failure connectivity", broken_color),
            ], className="kpi-grid")
        ], className="card")

        pb = R["prod_breakdown"]
        bar_fig = go.Figure(go.Bar(
            x=pb.values, y=pb.index, orientation="h",
            marker=dict(color=pb.values,
                        colorscale=[[0, "#6d5efc"], [0.5, "#a78bfa"], [1, "#22d3ee"]],
                        line=dict(width=0)),
            text=[fmt_usd(v) for v in pb.values],
            textposition="outside",
            textfont=dict(color=TEXT_DIM, size=11),
            hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>"
        ))
        bar_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=60, t=10, b=10), height=220,
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, color=TEXT_DIM, tickfont=dict(size=11)),
            font=dict(family="'Inter','Segoe UI',sans-serif")
        )

        route_rows = []
        for i, r in enumerate(R["top_routes"]):
            mode_col = TRANSPORT_COLORS.get(r["transport_mode"], "#888")
            route_rows.append(html.Div([
                html.Span(f"{i+1}", className="route-index"),
                html.Div([
                    html.Span(f"{r['from_country']} → {r['to_country']}",
                              style={"fontWeight": "700", "fontSize": "12px"}),
                    html.Span(f"  {r['product_category']}", style={"color": MUTED, "fontSize": "11px"})
                ], style={"flex": "1"}),
                html.Div([
                    html.Span(r["transport_mode"], style={"color": mode_col, "fontSize": "10px", "marginRight": "12px"}),
                    html.Span(f"{r['transit_days']}d", style={"color": MUTED, "fontSize": "10px", "marginRight": "12px"}),
                    html.Span(fmt_usd(r["trade_value_usd"]), style={"color": ACCENT, "fontWeight": "700", "fontSize": "12px"})
                ], style={"display": "flex", "alignItems": "center"})
            ], className="route-row"))

        alt_children = [html.P("No alternative sourcing routes found for the top affected product.",
                                className="empty-state")]
        if R["products"]:
            alternatives = find_alternatives(df, country, R["products"][0])
            if alternatives:
                alt_children = [
                    html.Div([
                        html.Div([
                            html.Span(a["alternative_country"], style={"fontWeight": "800"}),
                            badge(f"risk {a['country_risk_score']}", risk_color(a["country_risk_score"]))
                        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}),
                        html.Div(f"{a['product']} · {a['transport_mode']} · {a['transit_days']}d · "
                                 f"{fmt_usd(a['trade_value_usd'])}",
                                 style={"fontSize": "11px", "color": MUTED})
                    ], className="node-list-row", style={"flexDirection": "column", "alignItems": "stretch"})
                    for a in alternatives
                ]

        detail = html.Div([
            html.Div([
                html.Div([html.I(className="bi bi-bar-chart-fill me-2"), "Trade Exposure by Product"],
                         className="card-title", style={"color": ACCENT}),
                dcc.Graph(figure=bar_fig, config={"displayModeBar": False})
            ], className="card", style={"flex": "1", "minWidth": "320px"}),

            html.Div([
                html.Div([html.I(className="bi bi-signpost-split-fill me-2"), "Top Affected Routes"],
                         className="card-title", style={"color": WARNING}),
                *route_rows
            ], className="card", style={"flex": "1.2", "minWidth": "360px", "maxHeight": "320px", "overflowY": "auto"}),

            html.Div([
                html.Div([html.I(className="bi bi-signpost-2-fill me-2"), "Suggested Alternatives"],
                         className="card-title", style={"color": SUCCESS}),
                *alt_children
            ], className="card", style={"flex": "1", "minWidth": "280px"})
        ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"})

        return side, kpis, detail, "tab-disruption"

    except Exception as e:
        err = html.P(f"Error: {str(e)}", style={"color": DANGER, "fontSize": "12px"})
        return err, err, err, no_update


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
