import dash
from dash import dcc, html, Input, Output, State, no_update
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import base64, io, os, sys

from modules.risk_engine import calculate_route_risk, calculate_country_risk, find_single_points_of_failure, calculate_resilience_score
from modules.graph_engine import build_graph, get_critical_nodes
from modules.map_view import COUNTRY_COORDS


BG        = "#080810"
SURFACE   = "#10101a"
CARD      = "#13131f"
BORDER    = "#1e1530"
BORDER2   = "#2d1f45"
PINK      = "#e91e8c"
PINK_DIM  = "#7d1050"
PINK_PALE = "#f472b6"
PINK_GLOW = "#ff2d9510"
PURPLE    = "#7c3aed"
TEXT      = "#f0e6f6"
TEXT_DIM  = "#c4b5d4"
MUTED     = "#7a6d8a"
GREEN     = "#10b981"
AMBER     = "#f59e0b"
RED       = "#ef4444"
BLUE      = "#3b82f6"
FONT      = "'Inter','Segoe UI',sans-serif"


TRANSPORT_COLORS = {
    "Sea":      "#38bdf8",   # sky bl
    "Air":      "#a78bfa",   # violet
    "Road":     "#fb923c",   # orange
    "Rail":     "#34d399",   # emerald
    "Pipeline": "#f472b6",   # pink
}

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "TradeRoute Intelligence Platform"

def parse_csv(contents):
    _, b64 = contents.split(",", 1)
    return pd.read_csv(io.StringIO(base64.b64decode(b64).decode()))

def enrich_df(df):
    rng = np.random.default_rng(42)
    risk_cols = ["inform_risk","conflict_score","hazard_score","vulnerability_score","coping_capacity_score"]
    for prefix in ["from_","to_"]:
        for c in risk_cols:
            col = prefix + c
            if col not in df.columns:
                df[col] = rng.uniform(1, 8, len(df))
    df = calculate_route_risk(df)
    return df

def simulate_disruption_safe(df, country):
    df2 = df.copy()
    if "risk_level" in df2.columns:
        df2["risk_level"] = df2["risk_level"].astype(str)
    mask = (df2["from_country"] == country) | (df2["to_country"] == country)
    affected = df2[mask].copy()
    unaffected = df2[~mask].copy()
    total_loss = float(affected["trade_value_usd"].sum())
    products = affected["product_category"].unique().tolist()
    modes = affected["transport_mode"].unique().tolist()
    all_countries = set(df2["from_country"].tolist() + df2["to_country"].tolist())
    remaining = all_countries - {country}
    remaining_routes = unaffected[
        unaffected["from_country"].isin(remaining) &
        unaffected["to_country"].isin(remaining)
    ]
    connected_in_remaining = set(remaining_routes["from_country"].tolist() +
                                  remaining_routes["to_country"].tolist())
    isolated = remaining - connected_in_remaining
    network_broken = len(isolated) > 0
    avg_dep = float(affected["dependency_percent"].mean()) if len(affected) else 0
    top_routes = affected.nlargest(8, "trade_value_usd")[
        ["from_country","to_country","product_category","trade_value_usd","transport_mode","transit_days"]
    ].to_dict("records")
    prod_breakdown = (affected.groupby("product_category")["trade_value_usd"]
                      .sum().sort_values(ascending=False).head(6))
    return {
        "country": country,
        "total_loss": total_loss,
        "routes_affected": int(mask.sum()),
        "products": products,
        "modes": modes,
        "network_broken": network_broken,
        "isolated_count": len(isolated),
        "avg_dependency": avg_dep,
        "top_routes": top_routes,
        "prod_breakdown": prod_breakdown,
        "affected_df": affected,
    }

def risk_color(score):
    s = float(score)
    if s < 3:   return GREEN
    elif s < 6: return AMBER
    return RED

def risk_label(score):
    s = float(score)
    if s < 3:   return "LOW"
    elif s < 6: return "MEDIUM"
    return "HIGH"

def fmt_usd(v):
    if v >= 1e9:  return f"${v/1e9:.2f}B"
    if v >= 1e6:  return f"${v/1e6:.1f}M"
    return f"${v:,.0f}"

def info_row(label, val, val_color=None):
    return html.Div([
        html.Span(label, style={"color": MUTED, "fontSize":"11px",
                                 "textTransform":"uppercase","letterSpacing":"0.1em"}),
        html.Span(str(val), style={"color": val_color or TEXT_DIM,
                                    "fontSize":"13px","fontWeight":"600"})
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
              "borderBottom":f"1px solid {BORDER}","paddingBottom":"7px","marginBottom":"7px"})

def badge(text, color):
    return html.Span(text, style={
        "background": color+"18","color":color,"border":f"1px solid {color}44",
        "borderRadius":"20px","padding":"2px 9px","fontSize":"10px",
        "fontWeight":"700","letterSpacing":"0.08em"
    })

def kpi_card(label, value, sub="", accent=PINK, width="160px"):
    return html.Div([
        html.Div(label, style={"fontSize":"9px","letterSpacing":"0.18em",
                                "color":MUTED,"textTransform":"uppercase","marginBottom":"10px"}),
        html.Div(str(value), style={"fontSize":"28px","fontWeight":"900",
                                     "color":accent,"lineHeight":"1","fontVariantNumeric":"tabular-nums"}),
        html.Div(sub, style={"fontSize":"11px","color":MUTED,"marginTop":"5px","lineHeight":"1.4"})
    ], style={"background":CARD,"border":f"1px solid {BORDER2}",
              "borderTop":f"3px solid {accent}","borderRadius":"12px",
              "padding":"18px 20px","minWidth":width,"flex":"1",
              "boxShadow":f"0 4px 24px {accent}0a"})


app.layout = html.Div([
    html.Div([
        html.Div([
            html.Div("✦", style={"color":PINK,"fontSize":"22px","marginRight":"12px"}),
            html.Div([
                html.H1("TRADEROUTE INTELLIGENCE PLATFORM",
                        style={"margin":0,"fontSize":"clamp(18px,2.4vw,34px)",
                               "letterSpacing":"0.14em","fontWeight":"900",
                               "background":f"linear-gradient(100deg,{PINK_PALE} 0%,{PINK} 50%,{PURPLE} 100%)",
                               "-webkit-background-clip":"text",
                               "-webkit-text-fill-color":"transparent",
                               "backgroundClip":"text"}),
                html.P("Global Supply Chain · Risk Intelligence · Disruption Simulation",
                       style={"margin":"3px 0 0","fontSize":"10px","letterSpacing":"0.22em",
                              "color":MUTED,"textTransform":"uppercase"})
            ])
        ], style={"display":"flex","alignItems":"center"}),
        html.Div([
            *[html.Div([
                html.Div(style={"width":"28px","height":"3px","borderRadius":"2px",
                                "background":col,"marginBottom":"3px"}),
                html.Div(mode, style={"fontSize":"9px","color":MUTED,"letterSpacing":"0.08em"})
            ], style={"textAlign":"center","marginLeft":"14px"})
            for mode, col in TRANSPORT_COLORS.items()]
        ], style={"display":"flex","alignItems":"flex-end"})
    ], style={"display":"flex","alignItems":"center","justifyContent":"space-between",
              "padding":"20px 36px","borderBottom":f"1px solid {BORDER}",
              "background":f"linear-gradient(135deg,{SURFACE} 0%,#150820 100%)"}),

    html.Div([
        dcc.Upload(id="upload-data",
            children=html.Div([
                html.Span("⬆  ", style={"color":PINK,"fontWeight":"700"}),
                html.Span("Upload Trade CSV",style={"fontWeight":"600","letterSpacing":"0.05em"}),
                html.Span("  —  drag & drop or click",style={"color":MUTED,"fontSize":"13px"})
            ]),
            style={"border":f"1.5px dashed {PINK_DIM}","borderRadius":"10px",
                   "padding":"13px 26px","cursor":"pointer","display":"inline-flex",
                   "alignItems":"center","background":"#0f0818","color":TEXT},
            multiple=False),
        html.Div(id="upload-status",
                 style={"marginLeft":"18px","fontSize":"13px","display":"flex","alignItems":"center"})
    ], style={"padding":"16px 36px","display":"flex","alignItems":"center",
              "borderBottom":f"1px solid {BORDER}","background":SURFACE}),

    html.Div([
        html.Div([
            dcc.Graph(id="trade-map",
                      style={"height":"600px","borderRadius":"14px","overflow":"hidden"},
                      config={"scrollZoom":True,"displayModeBar":True,
                              "modeBarButtonsToRemove":["select2d","lasso2d"],
                              "displaylogo":False},
                      figure=go.Figure(layout=go.Layout(
                          paper_bgcolor=BG, plot_bgcolor=BG,
                          geo=dict(bgcolor="#080810",showframe=False,
                                   showcoastlines=True,coastlinecolor="#1e1530",
                                   coastlinewidth=0.8,
                                   showland=True,landcolor="#0e0d18",
                                   showocean=True,oceancolor="#05060f",
                                   showlakes=True,lakecolor="#05060f",
                                   showcountries=True,countrycolor="#1a1530",countrywidth=0.5,
                                   showsubunits=False,
                                   projection_type="natural earth"),
                          margin=dict(l=0,r=0,t=0,b=0),
                          annotations=[dict(
                              text="Upload a trade CSV to visualise global routes & risk",
                              x=0.5,y=0.5,xref="paper",yref="paper",
                              showarrow=False,font=dict(color=MUTED,size=14,family=FONT))]
                      )))
        ], style={"flex":"1","minWidth":0,"borderRadius":"14px",
                  "border":f"1px solid {BORDER2}","overflow":"hidden"}),

        html.Div([
            html.Div([
                html.Div("◈  NODE PROFILE",
                         style={"fontSize":"9px","letterSpacing":"0.22em","color":PINK,
                                "fontWeight":"800","marginBottom":"14px"}),
                html.Div(id="hover-panel",
                         children=html.P("Hover over a country node to inspect its trade profile.",
                                         style={"color":MUTED,"fontSize":"12px","lineHeight":"1.8"}),
                         style={"overflowY":"auto","flex":"1"})
            ], style={"background":CARD,"borderRadius":"12px","border":f"1px solid {BORDER2}",
                      "padding":"18px","marginBottom":"12px","display":"flex",
                      "flexDirection":"column","minHeight":"260px","maxHeight":"295px"}),

            html.Div([
                html.Div("⚡  DISRUPTION SIM",
                         style={"fontSize":"9px","letterSpacing":"0.22em","color":AMBER,
                                "fontWeight":"800","marginBottom":"14px"}),
                html.Div(id="disruption-side",
                         children=html.P("Click any node to simulate its failure and see the cascade impact.",
                                         style={"color":MUTED,"fontSize":"12px","lineHeight":"1.8"}),
                         style={"overflowY":"auto","flex":"1"})
            ], style={"background":CARD,"borderRadius":"12px","border":f"1px solid {BORDER2}",
                      "padding":"18px","display":"flex","flexDirection":"column",
                      "flex":"1","minHeight":"250px"})

        ], style={"width":"290px","flexShrink":"0","display":"flex","flexDirection":"column",
                  "gap":"0","maxHeight":"600px"})

    ], style={"display":"flex","gap":"16px","padding":"20px 36px","alignItems":"stretch"}),

    html.Div(id="disruption-kpis", style={"padding":"0 36px 20px"}),

    html.Div(id="disruption-detail", style={"padding":"0 36px 36px"}),

    dcc.Store(id="store-df"),

], style={"fontFamily":FONT,"background":BG,"color":TEXT,"minHeight":"100vh","margin":0})

def build_map_figure(df, country_risk_df):
    fig = go.Figure()

    # 1. Choropleth base
    fig.add_trace(go.Choropleth(
        locations=country_risk_df["iso3"],
        z=country_risk_df["country_risk_score"],
        colorscale=[
            [0.0,  "#0a1628"], [0.2,  "#0d2137"],
            [0.4,  "#1a3a5c"], [0.55, "#2d5a8e"],
            [0.7,  "#7d2d5c"], [0.85, "#b82060"],
            [1.0,  "#e91e8c"]
        ],
        zmin=0, zmax=10,
        marker=dict(line=dict(color="#1e1530", width=0.4)),
        colorbar=dict(
            title=dict(text="Risk Score", font=dict(color=PINK_PALE, size=11)),
            tickfont=dict(color=MUTED, size=10),
            bgcolor=CARD, bordercolor=BORDER2, borderwidth=1,
            tickvals=[0,2,4,6,8,10],
            ticktext=["0 Safe","2","4","6","8","10 Critical"],
            thickness=12, len=0.6, x=1.01
        ),
        hoverinfo="skip",
        showscale=True
    ))

    # 2. Trade arcs per transport mode (separate traces for legend)
    max_val = df["trade_value_usd"].max()
    for mode, color in TRANSPORT_COLORS.items():
        subset = df[df["transport_mode"] == mode]
        for _, row in subset.iterrows():
            fc = COUNTRY_COORDS.get(row["from_country"], (0,0))
            tc = COUNTRY_COORDS.get(row["to_country"],   (0,0))
            if fc == (0,0) or tc == (0,0): continue
            lw = 0.8 + (row["trade_value_usd"] / max_val) * 4.5
            rl = str(row.get("risk_level","?"))
            fig.add_trace(go.Scattergeo(
                lon=[fc[1], tc[1]], lat=[fc[0], tc[0]],
                mode="lines",
                line=dict(width=lw, color=color),
                opacity=0.55,
                hovertemplate=(
                    f"<b>{row['from_country']} → {row['to_country']}</b><br>"
                    f"Product: {row['product_category']}<br>"
                    f"Value: {fmt_usd(row['trade_value_usd'])}<br>"
                    f"Mode: {mode}  |  Transit: {row['transit_days']}d<br>"
                    f"Route Risk: {rl}"
                    "<extra></extra>"
                ),
                showlegend=False
            ))

    # 3. Country node markers
    all_c = pd.concat([
        df[["from_country","from_iso3","from_country_risk"]].rename(
            columns={"from_country":"country","from_iso3":"iso3","from_country_risk":"risk_score"}),
        df[["to_country","to_iso3","to_country_risk"]].rename(
            columns={"to_country":"country","to_iso3":"iso3","to_country_risk":"risk_score"})
    ]).drop_duplicates(subset="iso3")

    lats, lons, texts, colors, sizes, cdata = [], [], [], [], [], []
    for _, row in all_c.iterrows():
        coords = COUNTRY_COORDS.get(row["country"], (0,0))
        if coords == (0,0): continue
        lats.append(coords[0]); lons.append(coords[1])
        r = float(row["risk_score"])
        colors.append(risk_color(r))
        out_r = df[df["from_country"]==row["country"]]
        in_r  = df[df["to_country"]==row["country"]]
        total = float(out_r["trade_value_usd"].sum() + in_r["trade_value_usd"].sum())
        prods = list(pd.concat([out_r["product_category"],in_r["product_category"]]).unique()[:3])
        sizes.append(8 + min(total / max_val * 14, 10))
        texts.append(
            f"<b>{row['country']}</b>  [{row['iso3']}]<br>"
            f"Risk: <b>{r:.2f}</b>  ({risk_label(r)})<br>"
            f"Trade Volume: <b>{fmt_usd(total)}</b><br>"
            f"Out: {len(out_r)} routes  In: {len(in_r)} routes<br>"
            f"Products: {', '.join(prods)}"
        )
        cdata.append(row["country"])

    fig.add_trace(go.Scattergeo(
        lon=lons, lat=lats, mode="markers",
        marker=dict(
            size=sizes, color=colors, symbol="circle",
            line=dict(width=1.5, color="rgba(255,255,255,0.25)"),
            opacity=0.95
        ),
        text=texts,
        hovertemplate="%{text}<br><i>Click to simulate disruption</i><extra></extra>",
        customdata=cdata,
        showlegend=False
    ))

    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG,
        geo=dict(
            bgcolor="#080810", showframe=False,
            showcoastlines=True, coastlinecolor="#1e1530", coastlinewidth=0.8,
            showland=True, landcolor="#0e0d18",
            showocean=True, oceancolor="#05060f",
            showlakes=True, lakecolor="#05060f",
            showcountries=True, countrycolor="#1a1530", countrywidth=0.5,
            projection_type="natural earth"
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        hoverlabel=dict(
            bgcolor=CARD, bordercolor=BORDER2,
            font=dict(color=TEXT, size=12, family=FONT)
        )
    )
    return fig


# ── CALLBACKS ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("store-df",       "data"),
    Output("trade-map",      "figure"),
    Output("upload-status",  "children"),
    Input("upload-data",     "contents"),
    State("upload-data",     "filename"),
    prevent_initial_call=True
)
def on_upload(contents, filename):
    if not contents:
        return no_update, no_update, no_update
    try:
        df = parse_csv(contents)
        df = enrich_df(df)
        country_risk_df = calculate_country_risk(df)
        fig = build_map_figure(df, country_risk_df)
        status = [
            html.Span("✓ ", style={"color":GREEN,"fontWeight":"bold"}),
            html.Span(f"{filename}  ·  {len(df)} routes  ·  "
                      f"{df['from_country'].nunique() + df['to_country'].nunique()} country endpoints",
                      style={"color":TEXT_DIM})
        ]
        return df.to_json(date_format="iso", orient="split"), fig, status
    except Exception as e:
        return no_update, no_update, [
            html.Span("✗ ", style={"color":RED,"fontWeight":"bold"}),
            html.Span(str(e), style={"color":RED,"fontSize":"12px"})
        ]


@app.callback(
    Output("hover-panel", "children"),
    Input("trade-map",    "hoverData"),
    State("store-df",     "data"),
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
        out_r = df[df["from_country"]==country]
        in_r  = df[df["to_country"]==country]
        total = float(out_r["trade_value_usd"].sum() + in_r["trade_value_usd"].sum())
        products = list(pd.concat([out_r["product_category"],in_r["product_category"]]).unique())
        modes    = list(pd.concat([out_r["transport_mode"],  in_r["transport_mode"]]).unique())
        combined = df[(df["from_country"]==country)|(df["to_country"]==country)]
        avg_risk = float(combined["route_risk_score"].mean()) if len(combined) else 0
        avg_dep  = float(combined["dependency_percent"].mean()) if len(combined) else 0
        iso3 = df[df["from_country"]==country]["from_iso3"].iloc[0] if len(out_r) else "—"
        rc = risk_color(avg_risk)

        return [
            html.Div([
                html.Span(country, style={"fontSize":"16px","fontWeight":"900","color":PINK_PALE}),
                html.Span(f"  {iso3}", style={"fontSize":"10px","color":MUTED,"letterSpacing":"0.15em"})
            ], style={"marginBottom":"12px","paddingBottom":"10px","borderBottom":f"1px solid {BORDER}"}),
            info_row("Total Trade Volume", fmt_usd(total), PINK_PALE),
            info_row("Outbound Routes", len(out_r)),
            info_row("Inbound Routes",  len(in_r)),
            info_row("Avg Dependency", f"{avg_dep:.1f}%"),
            html.Div([
                html.Span("Route Risk", style={"color":MUTED,"fontSize":"11px",
                                                "textTransform":"uppercase","letterSpacing":"0.1em"}),
                badge(f"{risk_label(avg_risk)}  {avg_risk:.2f}", rc)
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                      "borderBottom":f"1px solid {BORDER}","paddingBottom":"8px","marginBottom":"8px"}),
            html.Div([
                html.Span("Modes", style={"color":MUTED,"fontSize":"10px",
                                           "textTransform":"uppercase","letterSpacing":"0.1em",
                                           "display":"block","marginBottom":"5px"}),
                html.Div([
                    html.Span(m, style={"background":TRANSPORT_COLORS.get(m,"#555")+"22",
                                        "color":TRANSPORT_COLORS.get(m,"#aaa"),
                                        "border":f"1px solid {TRANSPORT_COLORS.get(m,'#555')}44",
                                        "borderRadius":"4px","padding":"1px 7px",
                                        "fontSize":"10px","marginRight":"4px"})
                    for m in modes
                ])
            ], style={"marginBottom":"8px"}),
            html.Div([
                html.Span("Products", style={"color":MUTED,"fontSize":"10px",
                                              "textTransform":"uppercase","letterSpacing":"0.1em",
                                              "display":"block","marginBottom":"5px"}),
                html.Div([
                    html.Span(p, style={"background":PINK+"15","color":PINK_PALE,
                                        "border":f"1px solid {PINK_DIM}",
                                        "borderRadius":"4px","padding":"2px 6px",
                                        "fontSize":"10px","marginRight":"3px","marginBottom":"3px",
                                        "display":"inline-block"})
                    for p in products[:6]
                ])
            ])
        ]
    except Exception:
        return no_update


@app.callback(
    Output("disruption-side",  "children"),
    Output("disruption-kpis",  "children"),
    Output("disruption-detail","children"),
    Input("trade-map",         "clickData"),
    State("store-df",          "data"),
    prevent_initial_call=True
)
def on_click(clickData, df_json):
    if not clickData or not df_json:
        return no_update, no_update, no_update
    try:
        pt = clickData["points"][0]
        if "customdata" not in pt:
            return no_update, no_update, no_update

        country = pt["customdata"]
        df = pd.read_json(io.StringIO(df_json), orient="split")
        if "risk_level" in df.columns:
            df["risk_level"] = df["risk_level"].astype(str)

        R = simulate_disruption_safe(df, country)

        tv_fmt = fmt_usd(R["total_loss"])
        broken_color = RED if R["network_broken"] else GREEN
        broken_txt   = f"{R['isolated_count']} isolated" if R["network_broken"] else "Intact"

        # ── SIDE PANEL MINI-SUMMARY ──────────────────────────────────────────
        side = [
            html.Div([
                html.Span("Simulating: ", style={"color":MUTED,"fontSize":"11px"}),
                html.Span(country, style={"color":AMBER,"fontWeight":"800","fontSize":"13px"})
            ], style={"marginBottom":"10px","paddingBottom":"8px","borderBottom":f"1px solid {BORDER}"}),
            info_row("Trade at Risk",    tv_fmt,  PINK),
            info_row("Routes Cut",       R["routes_affected"], RED),
            info_row("Products Hit",     len(R["products"]), AMBER),
            info_row("Avg Dependency",   f"{R['avg_dependency']:.1f}%"),
            html.Div([
                html.Span("Network", style={"color":MUTED,"fontSize":"11px",
                                             "textTransform":"uppercase","letterSpacing":"0.1em"}),
                badge(broken_txt, broken_color)
            ], style={"display":"flex","justifyContent":"space-between","alignItems":"center"})
        ]

        # ── KPI CARDS ROW ────────────────────────────────────────────────────
        kpis = html.Div([
            html.Div([
                html.Span("⚡ DISRUPTION IMPACT — ", style={"color":AMBER,"fontWeight":"700","fontSize":"12px","letterSpacing":"0.12em"}),
                html.Span(f"Simulating failure of {country}",
                          style={"color":PINK_PALE,"fontWeight":"700","fontSize":"13px"})
            ], style={"width":"100%","marginBottom":"14px"}),
            html.Div([
                kpi_card("Trade at Risk",      tv_fmt,
                         "Immediate exposure",   PINK),
                kpi_card("Routes Disrupted",   R["routes_affected"],
                         "Direct connections",   RED),
                kpi_card("Products Affected",  len(R["products"]),
                         ", ".join(R["products"][:2]) + ("…" if len(R["products"])>2 else ""),
                         PURPLE),
                kpi_card("Avg Dependency",     f"{R['avg_dependency']:.1f}%",
                         "On disrupted country", AMBER),
                kpi_card("Network Status",     broken_txt,
                         "Post-failure connectivity", broken_color),
            ], style={"display":"flex","flexWrap":"wrap","gap":"12px"})
        ], style={"background":CARD,"border":f"1px solid {BORDER2}",
                  "borderTop":f"3px solid {AMBER}","borderRadius":"14px",
                  "padding":"20px 24px","boxShadow":f"0 4px 32px {AMBER}08"})

        # ── PRODUCT BREAKDOWN BAR CHART ──────────────────────────────────────
        pb = R["prod_breakdown"]
        bar_fig = go.Figure(go.Bar(
            x=pb.values, y=pb.index, orientation="h",
            marker=dict(
                color=pb.values,
                colorscale=[[0,"#7c3aed"],[0.5,"#e91e8c"],[1,"#f472b6"]],
                line=dict(width=0)
            ),
            text=[fmt_usd(v) for v in pb.values],
            textposition="outside",
            textfont=dict(color=TEXT_DIM, size=11),
            hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>"
        ))
        bar_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0,r=60,t=10,b=10), height=220,
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False,
                       color=MUTED),
            yaxis=dict(showgrid=False, color=TEXT_DIM, tickfont=dict(size=11)),
            hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER2,
                            font=dict(color=TEXT, size=12))
        )

        route_rows = []
        for i, r in enumerate(R["top_routes"]):
            mode_col = TRANSPORT_COLORS.get(r["transport_mode"],"#888")
            route_rows.append(html.Div([
                html.Span(f"{i+1}", style={"color":MUTED,"fontSize":"10px",
                                            "width":"16px","flexShrink":"0"}),
                html.Div([
                    html.Span(f"{r['from_country']} → {r['to_country']}",
                              style={"color":TEXT,"fontWeight":"700","fontSize":"12px"}),
                    html.Span(f"  {r['product_category']}",
                              style={"color":MUTED,"fontSize":"11px"})
                ], style={"flex":"1"}),
                html.Div([
                    html.Span(f"{r['transport_mode']}", style={"color":mode_col,"fontSize":"10px",
                                                                "marginRight":"12px"}),
                    html.Span(f"{r['transit_days']}d", style={"color":MUTED,"fontSize":"10px",
                                                               "marginRight":"12px"}),
                    html.Span(fmt_usd(r["trade_value_usd"]), style={"color":PINK,"fontWeight":"700",
                                                                      "fontSize":"12px"})
                ], style={"display":"flex","alignItems":"center"})
            ], style={"display":"flex","alignItems":"center","gap":"10px",
                      "borderBottom":f"1px solid {BORDER}","paddingBottom":"8px",
                      "marginBottom":"8px"}))

        detail = html.Div([
            html.Div([
                # bar chart card
                html.Div([
                    html.Div("TRADE EXPOSURE BY PRODUCT",
                             style={"fontSize":"9px","letterSpacing":"0.2em","color":PINK,
                                    "fontWeight":"800","marginBottom":"8px"}),
                    dcc.Graph(figure=bar_fig, config={"displayModeBar":False},
                              style={"height":"220px"})
                ], style={"background":CARD,"borderRadius":"12px","border":f"1px solid {BORDER2}",
                          "padding":"18px 20px","flex":"1","minWidth":"320px"}),

                # top routes card
                html.Div([
                    html.Div("TOP AFFECTED ROUTES",
                             style={"fontSize":"9px","letterSpacing":"0.2em","color":AMBER,
                                    "fontWeight":"800","marginBottom":"12px"}),
                    *route_rows
                ], style={"background":CARD,"borderRadius":"12px","border":f"1px solid {BORDER2}",
                          "padding":"18px 20px","flex":"2","minWidth":"420px","overflowY":"auto",
                          "maxHeight":"280px"})
            ], style={"display":"flex","gap":"14px","flexWrap":"wrap"})
        ])

        return side, kpis, detail

    except Exception as e:
        err = html.P(f"Error: {str(e)}", style={"color":RED,"fontSize":"12px"})
        return err, err, err


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
