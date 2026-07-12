# TradeRoute Intelligence Platform

> Global supply chain risk analysis, disruption simulation, and alternative sourcing — powered by graph analytics and interactive visualizations.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)
![Dash](https://img.shields.io/badge/Dash-2.0%2B-darkblue?style=flat-square&logo=plotly)
![Plotly](https://img.shields.io/badge/Plotly-5.0%2B-3F4F75?style=flat-square&logo=plotly)
![NetworkX](https://img.shields.io/badge/NetworkX-3.0%2B-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## Problem Statement

Global supply chains are increasingly vulnerable to disruptions — geopolitical conflicts, natural disasters, port closures, and trade restrictions can cut off critical routes overnight. Most businesses have no real-time visibility into which trade routes are high-risk, which countries are single points of failure, and what alternative sourcing options exist.

TradeRoute Intelligence Platform solves this by letting analysts upload trade data, visualize global routes on an interactive map, assess risk scores for every route and country, and simulate what happens when any node in the network is disrupted.

---

## Features

| Module | Description |
|---|---|
| Trade Map | Interactive globe with color-coded trade arcs by transport mode |
| Risk Engine | Multi-factor risk scoring for every route and country |
| Disruption Lab | Click any country to simulate its failure and see cascading impact |
| Network Resilience | Graph-based resilience score with single point of failure detection |
| Alternative Sourcing | Automatically suggests low-risk alternative suppliers on disruption |
| CSV Upload | Upload any trade dataset or load the built-in sample data |

---

## Architecture

```
TradeRoute Intelligence Platform/
│
├── app.py                  # Main Dash application and callbacks
│
├── modules/
│   ├── ingestion.py        # CSV parsing, validation, risk enrichment
│   ├── risk_engine.py      # Route risk, country risk, resilience scoring
│   ├── graph_engine.py     # NetworkX graph — centrality, disruption, alternatives
│   └── map_view.py         # Plotly choropleth and trade arc visualizations
│
├── assets/
│   └── style.css           # Custom dark UI styling
│
├── Data/
│   └── country_risk.csv    # INFORM risk scores by country
│
└── sample_trade.csv        # Built-in demo dataset
```

### Pipeline Flow

```
Input                  Processing                    Output
─────                  ──────────                    ──────
CSV Upload       →     Column Validation       →     Validated DataFrame
Trade Data       →     Risk Score Enrichment   →     Route Risk Scores
Country Data     →     Weighted Risk Formula   →     Country Risk Map
Trade Network    →     NetworkX Graph Build    →     Centrality Scores
Country Click    →     Disruption Simulation   →     Impact Analysis
Disrupted Route  →     Alternative Search      →     Sourcing Options
```

---

## Risk Scoring Model

### Route Risk Score
Each trade route is scored using a weighted formula:

```
Route Risk = (Origin Country Risk × 0.30)
           + (Destination Country Risk × 0.30)
           + (Transport Mode Risk × 0.20)
           + (Dependency % / 10 × 0.20)
```

Transport mode risk values: Rail (4.0) > Road (3.5) > Sea (3.0) > Pipeline (2.5) > Air (2.0)

### Country Risk Score
Derived from INFORM Risk Index components:

```
Country Risk = (INFORM Risk × 0.35)
             + (Conflict Score × 0.30)
             + (Hazard Score × 0.20)
             + (Vulnerability Score × 0.15)
```

### Network Resilience Score
```
Resilience = 10 - Avg Route Risk - (SPOF Count × 0.5) - (High Risk Routes × 0.3)
```
Capped between 0 (fragile) and 10 (robust).

---

## Graph Analytics

Built on **NetworkX DiGraph** where:
- **Nodes** = countries with risk score attributes
- **Edges** = trade routes with value, transport mode, transit days, dependency

Key metrics computed:
- **Betweenness Centrality** — identifies transit hubs critical to network flow
- **Degree Centrality** — measures connection density per country
- **Criticality Score** = Betweenness (0.6) + Degree (0.4)
- **Single Points of Failure** — countries with avg dependency > 60%

---

## Disruption Simulation

When a country node is removed from the graph:
1. All connected trade routes are identified
2. Total trade value at risk is calculated
3. Affected product categories are listed
4. Network connectivity is re-evaluated — isolated nodes detected
5. Top 8 highest-value affected routes are displayed
6. Alternative low-risk suppliers are suggested for the top product category

---

## Getting Started

### Prerequisites

- Python 3.8 or above
- Internet connection (for Google Fonts in UI)

### Installation

```bash
# Clone the repository
cd trade-route-intelligence-platform

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

The app will open at `http://localhost:8050`

> Note: Upload your own trade CSV or click **Load Sample Dataset** to explore with built-in data.

---

## Input Data Format

The platform accepts CSV files with the following required columns:

| Column | Description |
|---|---|
| from_country | Exporting country name |
| from_iso3 | ISO3 country code of exporter |
| to_country | Importing country name |
| to_iso3 | ISO3 country code of importer |
| product_category | Type of goods traded |
| trade_value_usd | Trade value in USD |
| transport_mode | Sea / Air / Road / Rail / Pipeline |
| transit_days | Number of days in transit |
| dependency_percent | % dependency on this route |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | Plotly Dash |
| Graph Analytics | NetworkX |
| Visualizations | Plotly (Choropleth, Scattergeo, Bar) |
| Risk Data | INFORM Risk Index |
| UI Styling | Custom CSS — dark theme |
| Data Processing | Pandas, NumPy |
| Deployment | Render (Gunicorn) |

---

## Key Design Decisions

**Why Dash over Streamlit?**
TradeRoute requires complex bidirectional interactivity — clicking a country on the map triggers a disruption simulation, which updates multiple panels simultaneously. Dash's callback architecture handles this reactive pattern natively, whereas Streamlit reruns the entire script on each interaction.

**Why NetworkX for supply chain modeling?**
Supply chains are fundamentally graphs — countries are nodes, trade routes are directed edges. NetworkX provides betweenness centrality, connectivity checks, and node removal in a few lines, making disruption simulation mathematically rigorous rather than just filtering a dataframe.

**Why weighted risk formula over ML?**
The INFORM Risk Index already provides validated, peer-reviewed risk scores for every country. Combining these with transport mode and dependency weights gives a transparent, explainable risk score — critical in supply chain contexts where analysts need to justify risk decisions to stakeholders.

---

## Future Improvements

- Real-time trade data integration via UN Comtrade API
- Time-series risk trend visualization per country
- Multi-country simultaneous disruption simulation
- Port-level granularity with shipping lane data
- Export disruption reports as PDF

---

## License

MIT License — free to use, modify, and distribute.
