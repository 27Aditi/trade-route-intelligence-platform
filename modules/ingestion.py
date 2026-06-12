import pandas as pd
import os

def load_trade_data(uploaded_file = None):

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, '..', 'Data', 'sample_trade.csv')
        df = pd.read_csv(file_path)

    return df

def validate_columns(df):

    required_columns = [
        'from_country', 'from_iso3', 'to_country', 'to_iso3', 'product_category', 
        'trade_value_usd', 'transport_mode', 'transit_days','dependency_percent'
    ]

    checklist = []
    for i in required_columns:
        if i not in df.columns:
            checklist.append(i)
    if(len(checklist) > 0):
        return False, checklist
    
    return True, checklist

def enrich_with_risk(trade_df):

    base_dir = os.path.dirname(os.path.abspath(__file__))
    risk_path = os.path.join(base_dir, '..', 'Data', 'country_risk.csv')
    risk_df = pd.read_csv(risk_path)

    risk_cols = ['inform_risk', 'hazard_score', 'conflict_score', 'vulnerability_score', 'coping_capacity_score']

    df = pd.merge(trade_df, risk_df, left_on = 'from_iso3', right_on = 'iso3', how = 'left')
    df = df.drop(columns = ['iso3', 'country'])
    df = df.rename(columns = {col : f'from_{col}' for col in risk_cols})

    df = pd.merge(df, risk_df, left_on = 'to_iso3', right_on = 'iso3', how = 'left')
    df = df.drop(columns = ['iso3', 'country'])
    df = df.rename(columns = {col : f'to_{col}' for col in risk_cols})

    return df

def get_summary(df):

    from_countries = set(df['from_country'].unique())
    to_countries = set(df['to_country'].unique())
    all_countries = from_countries.union(to_countries)

    summary = {
        'total_trade_value' : df['trade_value_usd'].sum(),
        'num_countries' : len(all_countries),
        'num_routes' : len(df),
        'num_products' : df['product_category'].nunique()
    }

    return summary



