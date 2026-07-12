import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

COUNTRY_COORDS = {
    'Afghanistan': (33.9391, 67.7100), 'Albania': (41.1533, 20.1683),
    'Algeria': (28.0339, 1.6596), 'Angola': (11.2027, 17.8739),
    'Argentina': (-38.4161, -63.6167), 'Australia': (-25.2744, 133.7751),
    'Austria': (47.5162, 14.5501), 'Azerbaijan': (40.1431, 47.5769),
    'Bangladesh': (23.6850, 90.3563), 'Belarus': (53.7098, 27.9534),
    'Belgium': (50.5039, 4.4699), 'Bolivia': (-16.2902, -63.5887),
    'Brazil': (-14.2350, -51.9253), 'Bulgaria': (42.7339, 25.4858),
    'Cambodia': (12.5657, 104.9910), 'Cameroon': (7.3697, 12.3547),
    'Canada': (56.1304, -106.3468), 'Chile': (-35.6751, -71.5430),
    'China': (35.8617, 104.1954), 'Colombia': (4.5709, -74.2973),
    'Congo': (-0.2280, 15.8277), 'Croatia': (45.1000, 15.2000),
    'Cuba': (21.5218, -77.7812), 'Czech Republic': (49.8175, 15.4730),
    'Denmark': (56.2639, 9.5018), 'Ecuador': (-1.8312, -78.1834),
    'Egypt': (26.8206, 30.8025), 'Ethiopia': (9.1450, 40.4897),
    'Finland': (61.9241, 25.7482), 'France': (46.2276, 2.2137),
    'Germany': (51.1657, 10.4515), 'Ghana': (7.9465, -1.0232),
    'Greece': (39.0742, 21.8243), 'Guatemala': (15.7835, -90.2308),
    'Hungary': (47.1625, 19.5033), 'India': (20.5937, 78.9629),
    'Indonesia': (-0.7893, 113.9213), 'Iran': (32.4279, 53.6880),
    'Iraq': (33.2232, 43.6793), 'Ireland': (53.1424, -7.6921),
    'Israel': (31.0461, 34.8516), 'Italy': (41.8719, 12.5674),
    'Japan': (36.2048, 138.2529), 'Jordan': (30.5852, 36.2384),
    'Kazakhstan': (48.0196, 66.9237), 'Kenya': (-0.0236, 37.9062),
    'Kuwait': (29.3117, 47.4818), 'Libya': (26.3351, 17.2283),
    'Malaysia': (4.2105, 101.9758), 'Mexico': (23.6345, -102.5528),
    'Morocco': (31.7917, -7.0926), 'Mozambique': (-18.6657, 35.5296),
    'Myanmar': (21.9162, 95.9560), 'Nepal': (28.3949, 84.1240),
    'Netherlands': (52.1326, 5.2913), 'New Zealand': (-40.9006, 174.8860),
    'Nigeria': (9.0820, 8.6753), 'Norway': (60.4720, 8.4689),
    'Pakistan': (30.3753, 69.3451), 'Peru': (-9.1900, -75.0152),
    'Philippines': (12.8797, 121.7740), 'Poland': (51.9194, 19.1451),
    'Portugal': (39.3999, -8.2245), 'Qatar': (25.3548, 51.1839),
    'Romania': (45.9432, 24.9668), 'Russia': (61.5240, 105.3188),
    'Saudi Arabia': (23.8859, 45.0792), 'Senegal': (14.4974, -14.4524),
    'Serbia': (44.0165, 21.0059), 'Singapore': (1.3521, 103.8198),
    'Somalia': (5.1521, 46.1996), 'South Africa': (-30.5595, 22.9375),
    'South Korea': (35.9078, 127.7669), 'Spain': (40.4637, -3.7492),
    'Sri Lanka': (7.8731, 80.7718), 'Sudan': (12.8628, 30.2176),
    'Sweden': (60.1282, 18.6435), 'Switzerland': (46.8182, 8.2275),
    'Syria': (34.8021, 38.9968), 'Taiwan': (23.5937, 121.0254),
    'Tanzania': (-6.3690, 34.8888), 'Thailand': (15.8700, 100.9925),
    'Turkey': (38.9637, 35.2433), 'UAE': (23.4241, 53.8478),
    'Uganda': (1.3733, 32.2903), 'Ukraine': (48.3794, 31.1656),
    'United Arab Emirates': (23.4241, 53.8478),
    'United Kingdom': (55.3781, -3.4360),
    'United States': (37.0902, -95.7129),
    'USA': (37.0902, -95.7129),
    'Uruguay': (-32.5228, -55.7658), 'Uzbekistan': (41.3775, 64.5853),
    'Venezuela': (6.4238, -66.5897), 'Vietnam': (14.0583, 108.2772),
    'Yemen': (15.5527, 48.5164), 'Zambia': (-13.1339, 27.8493),
    'Zimbabwe': (-19.0154, 29.1549)
}

TRANSPORT_COLORS = {
    'Sea': '#38bdf8',
    'Air': '#a78bfa',
    'Road': '#fb923c',
    'Rail': '#34d399',
    'Pipeline': '#f472b6'
}

DARK_GEO = dict(
    showframe=False,
    showcoastlines=True,
    coastlinecolor='#232437',
    coastlinewidth=0.8,
    showland=True,
    landcolor='#12131c',
    showocean=True,
    oceancolor='#0a0b12',
    showlakes=True,
    lakecolor='#0a0b12',
    showcountries=True,
    countrycolor='#1d1e2c',
    countrywidth=0.5,
    projection_type='natural earth',
    bgcolor='rgba(0,0,0,0)'
)


def get_coords(country_name):
    return COUNTRY_COORDS.get(country_name, (0, 0))


def draw_choropleth(country_risk_df):

    fig = px.choropleth(
        country_risk_df,
        locations='iso3',
        color='country_risk_score',
        hover_name='country',
        hover_data={
            'country_risk_score': ':.2f',
            'conflict_score': ':.2f',
            'vulnerability_score': ':.2f',
            'iso3': False
        },
        color_continuous_scale=[
            [0.0, '#22c55e'],
            [0.3, '#eab308'],
            [0.6, '#f97316'],
            [1.0, '#ef4444']
        ],
        range_color=[0, 10],
        labels={'country_risk_score': 'Risk Score'}
    )

    fig.update_layout(
        geo=DARK_GEO,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_colorbar=dict(
            title='Risk',
            tickvals=[0, 2, 4, 6, 8, 10],
            ticktext=['0', '2', '4', '6', '8', '10'],
            thickness=10,
            len=0.55,
            x=1.0,
            bgcolor='rgba(0,0,0,0)',
            tickfont=dict(color='#8a8ca3', size=10),
            title_font=dict(color='#c7c9dc', size=11)
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        font=dict(family="'Inter','Segoe UI',sans-serif")
    )

    return fig


def draw_trade_arcs(df, fig):

    max_value = df['trade_value_usd'].max()

    for mode, color in TRANSPORT_COLORS.items():
        subset = df[df['transport_mode'] == mode]
        for _, row in subset.iterrows():
            from_coords = get_coords(row['from_country'])
            to_coords = get_coords(row['to_country'])

            if from_coords == (0, 0) or to_coords == (0, 0):
                continue

            line_width = 0.8 + (row['trade_value_usd'] / max_value) * 4.5

            fig.add_trace(go.Scattergeo(
                lon=[from_coords[1], to_coords[1]],
                lat=[from_coords[0], to_coords[0]],
                mode='lines',
                line=dict(width=line_width, color=color),
                opacity=0.6,
                hovertemplate=(
                    f"<b>{row['from_country']} → {row['to_country']}</b><br>"
                    f"Product: {row['product_category']}<br>"
                    f"Value: ${row['trade_value_usd']:,.0f}<br>"
                    f"Mode: {mode} · Transit: {row['transit_days']}d<br>"
                    f"Risk: {row.get('risk_level','—')}"
                    "<extra></extra>"
                ),
                showlegend=False
            ))

    return fig


def draw_node_markers(df, fig):

    all_countries = pd.concat([
        df[['from_country', 'from_iso3', 'from_country_risk']].rename(
            columns={'from_country': 'country', 'from_iso3': 'iso3',
                     'from_country_risk': 'risk_score'}),
        df[['to_country', 'to_iso3', 'to_country_risk']].rename(
            columns={'to_country': 'country', 'to_iso3': 'iso3',
                     'to_country_risk': 'risk_score'})
    ]).drop_duplicates(subset='iso3')

    max_value = df['trade_value_usd'].max()
    lats, lons, texts, colors, sizes, customdata = [], [], [], [], [], []

    for _, row in all_countries.iterrows():
        coords = get_coords(row['country'])
        if coords == (0, 0):
            continue

        out_r = df[df['from_country'] == row['country']]
        in_r = df[df['to_country'] == row['country']]
        total = float(out_r['trade_value_usd'].sum() + in_r['trade_value_usd'].sum())

        lats.append(coords[0])
        lons.append(coords[1])
        risk = float(row['risk_score'])

        if risk < 3:
            colors.append('#22c55e')
        elif risk < 6:
            colors.append('#f59e0b')
        else:
            colors.append('#ef4444')

        sizes.append(9 + min(total / max_value * 16, 14))
        texts.append(
            f"<b>{row['country']}</b>  [{row['iso3']}]<br>"
            f"Risk: <b>{risk:.2f}</b><br>"
            f"Trade Volume: <b>${total:,.0f}</b><br>"
            f"Routes: {len(out_r) + len(in_r)}<br>"
            f"<i>Click to simulate disruption</i>"
        )
        customdata.append(row['country'])

    fig.add_trace(go.Scattergeo(
        lon=lons,
        lat=lats,
        mode='markers',
        marker=dict(
            size=sizes,
            color=colors,
            symbol='circle',
            line=dict(width=1.4, color='rgba(255,255,255,0.3)'),
            opacity=0.95
        ),
        text=texts,
        hovertemplate="%{text}<extra></extra>",
        customdata=customdata,
        showlegend=False
    ))

    return fig


def build_full_map(df, country_risk_df):
    fig = draw_choropleth(country_risk_df)
    fig = draw_trade_arcs(df, fig)
    fig = draw_node_markers(df, fig)
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        hoverlabel=dict(
            bgcolor='#171822',
            bordercolor='#2e2f3d',
            font=dict(color='#e8e9f3', size=12, family="'Inter','Segoe UI',sans-serif")
        )
    )
    return fig
