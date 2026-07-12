# TradeRoute Intelligence Platform — Global Supply Chain Risk & Disruption Simulator

> **Interactive global trade network mapping, country & route risk scoring, and one-click disruption simulation — all in a single live dashboard.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Dash](https://img.shields.io/badge/Dash-2.x-informational?style=flat-square&logo=plotly)](https://dash.plotly.com/)
[![Plotly](https://img.shields.io/badge/Plotly-Graphing-purple?style=flat-square&logo=plotly)](https://plotly.com/python/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](#-license)

**🔗 Live Demo:** [trade-route-intelligence-platform.onrender.com](https://trade-route-intelligence-platform.onrender.com/)

---

## Problem Statement

Global supply chains are dense, interdependent networks — a single port closure, a border conflict, or a sanctioned country can cascade into losses far beyond the immediate trade lane. Yet most trade dashboards only show **historical numbers**: import/export volumes, tariffs, and country stats. They don't answer the question that actually matters to risk teams —

**"If this country or route disappeared tomorrow, what would break?"**

**TradeRoute Intelligence Platform solves this** by turning a raw trade dataset into a live global network graph, scoring every route and country for geopolitical/logistics risk, and letting the user **click a country to simulate its failure** — instantly surfacing the trade value at risk, the routes cut, the products affected, and whether the remaining network fragments into isolated clusters.

---

## Features

| Module                     | Description                                                                                       |
| --------------------------- | --------------------------------------------------------------------------------------------------- |
| 🗺️ **Live Trade Map**        | Interactive world map plotting every trade route as a colour-coded arc by transport mode (Sea/Air/Road/Rail/Pipeline) |
| 🌡️ **Country Risk Choropleth** | Every country shaded by an aggregated risk score (conflict, hazard, vulnerability, coping capacity) |
| 📈 **Route Risk Scoring**    | Each trade lane classified LOW / MEDIUM / HIGH risk based on origin–destination risk inputs         |
| 🖱️ **Node Profile on Hover** | Hover any country to see trade volume, inbound/outbound route counts, dependency %, transport modes and products |
| ⚡ **Disruption Simulator**  | Click any country to simulate its sudden failure — cascading trade loss, routes cut, network fragmentation |
| 🕸️ **Network Resilience**    | Detects single points of failure and isolated clusters once a node is removed from the network      |
| 📊 **Impact KPIs**           | Auto-generated KPI cards: Trade at Risk, Routes Disrupted, Products Affected, Avg Dependency, Network Status |
| 📁 **Bring Your Own Data**   | Drag-and-drop CSV upload — works with any trade dataset following the expected schema               |

---

## Architecture

```
trade-route-intelligence-platform/
│
├── app.py                     # Main Dash application, layout, callbacks & map rendering
│
├── modules/
│   ├── risk_engine.py          # Route & country risk scoring, SPOF detection, resilience scoring
│   ├── graph_engine.py         # Trade network graph construction, critical node detection
│   └── map_view.py             # Country → lat/lon coordinate lookup for geo-plotting
│
├── Data/                       # Reference / supporting datasets
├── sample_trade.csv            # Example trade dataset to try the platform instantly
└── requirements.txt
```

### Pipeline Flow

```
Data Source              Processing                          Output
────────────             ──────────                          ──────
Uploaded Trade CSV   →   Risk Enrichment (risk_engine.py) →   Route & Country Risk Scores
                     →   Graph Construction (graph_engine.py) → Critical Nodes / SPOFs
                     →   Coordinate Mapping (map_view.py)  →   Global Route Map
User clicks a node   →   Disruption Simulation             →   Cascade Impact + KPI Cards
User hovers a node   →   Node Aggregation                  →   Trade Profile Panel
```

---

## Core Engine Components

### 1. Risk Engine (`risk_engine.py`)
- Computes a **route risk score** for every trade lane from origin/destination inputs such as INFORM risk, conflict score, hazard score, vulnerability score, and coping capacity
- Aggregates route-level scores into a **country risk score** used to shade the choropleth map
- Identifies **single points of failure (SPOFs)** — countries whose removal disconnects parts of the network
- Produces a **network resilience score** summarising how robust the overall trade graph is

### 2. Graph Engine (`graph_engine.py`)
- Builds a directed trade network graph from the uploaded dataset (`build_graph`)
- Ranks **critical nodes** by connectivity and trade dependency (`get_critical_nodes`)
- Feeds the disruption simulator's connectivity checks after a node is removed

### 3. Disruption Simulator (`app.py`)
- Removes a clicked country from the network and recomputes:
  - **Total trade value at risk** (sum of all routes touching that country)
  - **Routes cut** and **products affected**
  - **Average dependency %** of the impacted lanes
  - Whether the **remaining network fragments** into isolated country clusters
- Surfaces results as live KPI cards, a product-exposure bar chart, and a ranked list of the top affected routes

---

## Sample Data Schema

The platform accepts any CSV following this shape (see `sample_trade.csv` for a working example):

| Column                | Description                                   |
| ---------------------- | ---------------------------------------------- |
| `from_country` / `to_country` | Trade route origin and destination        |
| `from_iso3` / `to_iso3`       | ISO-3 country codes (used for map plotting) |
| `product_category`     | Product/commodity being traded                |
| `trade_value_usd`      | Trade value in USD                             |
| `transport_mode`       | Sea / Air / Road / Rail / Pipeline             |
| `transit_days`         | Transit time in days                           |
| `dependency_percent`   | % dependency of the destination on this route  |

> If risk-related columns (`inform_risk`, `conflict_score`, `hazard_score`, `vulnerability_score`, `coping_capacity_score`) are missing, the platform automatically generates seeded placeholder scores so the dashboard remains fully functional on any trade dataset.

---

## Getting Started

### Prerequisites
- Python 3.8 or above

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/27Aditi/trade-route-intelligence-platform.git
cd trade-route-intelligence-platform

# 2. (Recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

App will open at `http://localhost:8050`

> Upload `sample_trade.csv` to instantly explore the map, risk scores, and disruption simulator without needing your own dataset.

---

## Tech Stack

| Layer            | Technology                          |
| ------------------ | -------------------------------------- |
| Dashboard          | Dash (Plotly)                         |
| Visualization      | Plotly — Choropleth, Scattergeo, Bar  |
| Data Processing    | Pandas, NumPy                         |
| Backend Server     | Flask (via Dash's `app.server`)        |
| Deployment         | Render                                |
| Language           | Python                                 |

---

## Key Design Decisions

**Why Dash over Streamlit?** The dashboard is built around click and hover interactions on a live map (inspect a node, then click it to simulate disruption). Dash's callback model maps cleanly onto Plotly's native `hoverData` / `clickData` events, which makes this kind of stateful, event-driven interactivity far more natural than a script-rerun framework.

**Why simulate disruption by node removal instead of a static risk score?** A high risk score alone doesn't tell you the blast radius of a failure. Removing a country from the graph and recomputing connectivity shows the *actual* cascading consequence — cut routes, stranded trade value, and whether the rest of the network stays connected.

**Why auto-generate placeholder risk scores?** Real geopolitical risk indicators aren't always available in a user's trade dataset. Rather than blocking analysis, the platform seeds plausible risk values so anyone can upload their own trade CSV and get a fully working risk-and-disruption view immediately.

---

## Sample Output

- A world map of every trade lane, colour-coded by transport mode, over a risk-shaded country choropleth
- A hoverable trade profile for any country — volume, routes, dependency, products
- A one-click disruption simulation showing trade at risk, routes cut, and whether the network fractures
- A ranked breakdown of the products and routes most exposed to a given country's failure

---

## Future Improvements

- [ ] Live ingestion of real-world risk indicators (e.g., INFORM Risk Index, ACLED conflict data)
- [ ] Multi-node / simultaneous disruption scenarios
- [ ] Exportable PDF disruption reports
- [ ] Historical trend playback of trade flows over time
- [ ] Tariff- and currency-shock simulation alongside physical disruption
- [ ] Multi-user sessions with saved datasets

---

## Author

Built as a supply chain risk intelligence project demonstrating real-world application of network graph analysis, geospatial visualization, and interactive disruption simulation on global trade data.

---

## 📄 License

MIT License — free to use, modify, and distribute.
