import pandas as pd
import numpy as np

def calculate_country_risk(df):

    risk_df = df[['from_country', 'from_iso3', 'from_inform_risk', 'from_conflict_score', 'from_hazard_score', 'from_vulnerability_score', 'from_coping_capacity_score']].copy()
    risk_df.columns = ['country', 'iso3', 'inform_risk', 'conflict_score', 'hazard_score', 'vulnerability_score', 'coping_capacity_score']
    to_risk_df = df[['to_country', 'to_iso3', 'to_inform_risk', 'to_conflict_score', 'to_hazard_score', 'to_vulnerability_score', 'to_coping_capacity_score']].copy()
    to_risk_df.columns = ['country', 'iso3', 'inform_risk', 'conflict_score', 'hazard_score', 'vulnerability_score', 'coping_capacity_score']

    all_countries = pd.concat([risk_df, to_risk_df]).drop_duplicates(subset = 'iso3')

    all_countries['country_risk_score'] = (
        all_countries['inform_risk'] * 0.35 + 
        all_countries['conflict_score'] * 0.30 + 
        all_countries['hazard_score'] * 0.20 +
        all_countries['vulnerability_score'] * 0.15
    )

    return all_countries[['country', 'iso3', 'country_risk_score', 'inform_risk', 'conflict_score', 'vulnerability_score']]

def calculate_route_risk(df):

    transport_risk = {
        'Sea' : 3.0,
        'Air' : 2.0,
        'Rail' : 4.0,
        'Road' : 3.5, 
        'Pipeline' : 2.5
    }

    df = df.copy()

    df['transport_risk'] = df['transport_mode'].map(transport_risk).fillna(3.0)

    df['from_country_risk'] = (
        df['from_inform_risk'] * 0.35 +
        df['from_conflict_score'] * 0.30 + 
        df['from_hazard_score'] * 0.20 + 
        df['from_vulnerability_score'] * 0.15
    )

    df['to_country_risk'] = (
        df['to_inform_risk'] * 0.35 +
        df['to_conflict_score'] * 0.30 + 
        df['to_hazard_score'] * 0.20 +
        df['to_vulnerability_score'] * 0.15
    )

    df['route_risk_score'] = (
        df['from_country_risk'] * 0.30 +
        df['to_country_risk'] * 0.30 +
        df['transport_risk'] * 0.20 + 
        (df['dependency_percent'] / 10) * 0.20
    )

    df['risk_level'] = pd.cut(
        df['route_risk_score'],
        bins = [0, 3, 6, 10],
        labels = ['Low', 'Medium', 'High']
    )
    
    return df

def find_single_points_of_failure(df):

    spof = []

    country_dependency = df.groupby('from_country').agg(
        total_value = ('trade_value_usd', 'sum'),
        avg_dependency = ('dependency_percent', 'mean'),
        products = ('product_category', lambda x : list(x.unique()))).reset_index()
    
    spof_countries = country_dependency[
        country_dependency['avg_dependency'] > 60
    ]

    for _, row in spof_countries.iterrows():
        spof.append({
            'country' : row['from_country'],
            'avg_dependency' : round(row['avg_dependency'], 1),
            'total_exposure_usd' : row['total_value'],
            'products_at_risk' : row['products']
        })

    return spof

def calculate_resilience_score(df):
    avg_route_risk = df['route_risk_score'].mean()
    spof_count = len(find_single_points_of_failure(df))
    spof_penalty = spof_count * 0.5
    high_risk_routes = len(df[df['risk_level'] == 'High'])
    high_risk_penalty = high_risk_routes * 0.3
    resilience = 10 - avg_route_risk - spof_penalty - high_risk_penalty
    resilience = round(max(0, min(10, resilience)), 2)
    return resilience

