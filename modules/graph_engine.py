import networkx as nx
import pandas as pd
import numpy as np

def build_graph(df):

    G = nx.DiGraph()

    countries = pd.concat([
        df[['from_country', 'from_iso3', 'from_country_risk']].rename(columns = {'from_country' : 'country', 'from_iso3' : 'iso3', 'from_country_risk' : 'risk_score'}),
        df[['to_country', 'to_iso3', 'to_country_risk']].rename(columns = {'to_country' : 'country', 'to_iso3' : 'iso3', 'to_country_risk' : 'risk_score'})
    ]).drop_duplicates(subset = 'iso3')

    for _, row in countries.iterrows():
        G.add_node(row['country'],
                   iso3 = row['iso3'],
                   risk_score = row['risk_score'])

    for _, row in df.iterrows():
        G.add_edge(row['from_country'],
                   row['to_country'],
                   trade_value = row['trade_value_usd'],
                   transport_mode = row['transport_mode'],
                   transit_days = row['transit_days'],
                   dependency = row['dependency_percent'],
                   product = row['product_category'],
                   route_risk = row['route_risk_score']) 
        
    return G

def get_critical_nodes(G):

    betweenness = nx.betweenness_centrality(G, weight = 'trade_value')
    degree = nx.degree_centrality(G)
    critical = []
    for node in G.nodes():
        critical.append({
            'country' : node,
            'betweenness_score' : round(betweenness[node], 4),
            'degree_score' : round(degree[node], 4),
            'criticality_score' : round((betweenness[node] * 0.6) + (degree[node] * 0.4), 4),
            'risk_score' : G.nodes[node].get('risk_score', 0)
        })
    critical_df = pd.DataFrame(critical)
    critical_df = critical_df.sort_values('criticality_score', ascending=False)
    return critical_df

def simulate_disruption(df, G, country):
    affected_routes = df[
        (df['from_country'] == country) | (df['to_country'] == country)
    ]
    total_loss = affected_routes['trade_value_usd'].sum()
    num_routes_affected = len(affected_routes)
    products_affected = affected_routes['product_category'].unique().tolist()
    G_temp = G.copy()
    G_temp.remove_node(country)
    is_connected_before = nx.is_weakly_connected(G)
    is_connected_after = nx.is_weakly_connected(G_temp)
    network_broken = is_connected_before and not is_connected_after
    return {
        'disrupted_country' : country,
        'total_trade_loss_usd' : total_loss,
        'routes_affected' : num_routes_affected,
        'products_affected' : products_affected,
        'network_broken' : network_broken,
        'affected_routes_detail' : affected_routes[[
            'from_country', 'to_country', 'product_category', 'trade_value_usd', 'transport_mode'
        ]].to_dict('records')
    }

def find_alternatives(df, disrupted_country, product_category):
    alternatives = df[
        (df['product_cateory'] == product_category) & 
        (df['from_country'] != disrupted_country)
    ].copy()

    if len(alternatives) == 0:
        product_type = product_category.split()[0]
        alternatives = df[
            (df['product_category'].str.contains(product_type, case = False)) &
            (df['from_country'] != disrupted_country)
        ].copy()

    if len(alternatives) == 0:
        return []
    
    alternatives = alternatives.sort_values('from_country_risk', ascending = True)
    result = []

    for _, row in alternatives.head(3).iterrows():
        result.append({
            'alternative_country' : row['from_country'],
            'product' : row['product_category'],
            'country_risk_score' : round(row['from_country_risk'], 2),
            'transport_mode' : row['transport_mode'],
            'transit_days' : row['transit_days'],
            'trade_value_usd' : row['trade_value_usd']
        })
    return result
