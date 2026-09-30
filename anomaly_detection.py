"""
anomaly_detection.py - Business Anomaly Detection Module
=========================================================
Uses Isolation Forest from scikit-learn to detect unusual patterns
in business sales data.

Detects:
- Unusually high/low revenue transactions
- Unusual quantity orders
- Abnormal profit margins
- Suspicious transaction patterns
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

warnings.filterwarnings('ignore')

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


def load_sales_data():
    """Load all sales data with product info."""
    from database import get_db
    conn = get_db()
    df = pd.read_sql_query('''
        SELECT s.id, s.sale_date, s.product_id, s.customer_id, s.region,
               s.category, s.quantity, s.unit_price, s.revenue, s.cost, s.profit,
               p.product_name
        FROM sales s
        LEFT JOIN products p ON s.product_id = p.id
        ORDER BY s.sale_date
    ''', conn)
    conn.close()
    return df


def prepare_features(df):
    """
    Prepare numerical features for anomaly detection.

    Features:
    - revenue, quantity, unit_price, profit
    - profit_margin (profit/revenue)
    - price_quantity_ratio (unit_price * quantity)
    - cost_ratio (cost/revenue)
    """
    if df.empty:
        return None, None

    df = df.copy()
    df['profit_margin'] = np.where(df['revenue'] > 0, df['profit'] / df['revenue'], 0)
    df['price_quantity'] = df['unit_price'] * df['quantity']
    df['cost_ratio'] = np.where(df['revenue'] > 0, df['cost'] / df['revenue'], 1)

    feature_cols = ['revenue', 'quantity', 'unit_price', 'profit',
                    'profit_margin', 'price_quantity', 'cost_ratio']

    X = df[feature_cols].fillna(0).values

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, {
        'feature_cols': feature_cols,
        'scaler': scaler,
        'df': df
    }


def detect_anomalies(contamination=0.05, random_state=42):
    """
    Run Isolation Forest anomaly detection on sales data.

    Args:
        contamination: Expected proportion of anomalies (0.01-0.10)
        random_state: Random seed for reproducibility

    Returns:
        dict with anomaly results, scores, and statistics
    """
    if not ML_AVAILABLE:
        return {'error': 'scikit-learn not installed.'}

    df = load_sales_data()
    if df.empty:
        return {'error': 'No sales data found.'}

    X_scaled, meta = prepare_features(df)
    if X_scaled is None:
        return {'error': 'Could not prepare features.'}

    # Train Isolation Forest
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        max_samples='auto',
        random_state=random_state,
        n_jobs=-1
    )

    # Predict: -1 = anomaly, 1 = normal
    predictions = iso_forest.fit_predict(X_scaled)
    scores = iso_forest.decision_function(X_scaled)

    # Add results to dataframe
    df['anomaly'] = predictions
    df['anomaly_score'] = scores
    df['is_anomaly'] = df['anomaly'] == -1

    # Determine severity based on score magnitude
    score_abs = np.abs(scores)
    score_threshold_low = np.percentile(score_abs, 70)
    score_threshold_high = np.percentile(score_abs, 90)

    def get_severity(score):
        s = abs(score)
        if s >= score_threshold_high:
            return 'high'
        elif s >= score_threshold_low:
            return 'medium'
        return 'low'

    df['severity'] = df['anomaly_score'].apply(get_severity)

    # Generate human-readable descriptions for anomalies
    # Precompute quantiles for descriptions
    rev_q95 = df['revenue'].quantile(0.95)
    rev_q05 = df['revenue'].quantile(0.05)
    qty_q95 = df['quantity'].quantile(0.95)
    qty_q05 = df['quantity'].quantile(0.05)
    price_q95 = df['unit_price'].quantile(0.95)

    def describe_anomaly(row):
        parts = []
        if row['revenue'] > rev_q95:
            parts.append(f'Unusually high revenue (${row["revenue"]:,.0f})')
        elif row['revenue'] < rev_q05:
            parts.append(f'Unusually low revenue (${row["revenue"]:,.2f})')

        if row['quantity'] > qty_q95:
            parts.append(f'abnormally large quantity ({int(row["quantity"])})')
        elif row['quantity'] < qty_q05:
            parts.append(f'very small quantity ({int(row["quantity"])})')

        if row['profit'] < 0:
            parts.append(f'negative profit (${row["profit"]:,.2f})')

        margin = row.get('profit_margin', None)
        if margin is not None:
            if margin < 0:
                parts.append(f'negative margin ({margin*100:.1f}%)')
            elif margin > 0.9:
                parts.append(f'extremely high margin ({margin*100:.1f}%)')

        if row['unit_price'] > price_q95:
            parts.append(f'high unit price (${row["unit_price"]:,.2f})')

        if not parts:
            parts.append('unusual combination of values')

        return f'Anomaly: {"; ".join(parts)} in {row["region"]} ({row["category"]})'

    df['description'] = df.apply(lambda r: describe_anomaly(r) if r['is_anomaly'] else '', axis=1)

    # Separate anomalies and normal
    anomalies_df = df[df['is_anomaly']].copy()
    normal_df = df[~df['is_anomaly']].copy()

    # Statistics
    stats = {
        'total_records': len(df),
        'anomaly_count': len(anomalies_df),
        'anomaly_pct': round(len(anomalies_df) / len(df) * 100, 1),
        'high_severity': len(anomalies_df[anomalies_df['severity'] == 'high']),
        'medium_severity': len(anomalies_df[anomalies_df['severity'] == 'medium']),
        'low_severity': len(anomalies_df[anomalies_df['severity'] == 'low']),
        'avg_anomaly_revenue': float(anomalies_df['revenue'].mean()) if len(anomalies_df) > 0 else 0,
        'avg_normal_revenue': float(normal_df['revenue'].mean()) if len(normal_df) > 0 else 0,
    }

    # Anomalies by region
    by_region = anomalies_df.groupby('region').size().to_dict() if len(anomalies_df) > 0 else {}
    by_category = anomalies_df.groupby('category').size().to_dict() if len(anomalies_df) > 0 else {}

    # Save model
    model_path = os.path.join(MODELS_DIR, 'isolation_forest.joblib')
    joblib.dump({'model': iso_forest, 'scaler': meta['scaler'], 'feature_cols': meta['feature_cols']}, model_path)

    # Prepare anomaly records for display (top 50 by score magnitude)
    anomaly_records = []
    for _, row in anomalies_df.nsmallest(50, 'anomaly_score').iterrows():
        anomaly_records.append({
            'id': int(row['id']),
            'sale_date': row['sale_date'],
            'product_name': row.get('product_name', 'Unknown'),
            'region': row['region'],
            'category': row['category'],
            'quantity': int(row['quantity']),
            'unit_price': round(float(row['unit_price']), 2),
            'revenue': round(float(row['revenue']), 2),
            'profit': round(float(row['profit']), 2),
            'profit_margin': round(float(row.get('profit_margin', 0)) * 100, 1),
            'anomaly_score': round(float(row['anomaly_score']), 4),
            'severity': row['severity'],
            'description': row['description'],
        })

    # Prepare scatter data (all points with anomaly flag)
    scatter_data = []
    for _, row in df.iterrows():
        scatter_data.append({
            'revenue': round(float(row['revenue']), 2),
            'quantity': int(row['quantity']),
            'profit': round(float(row['profit']), 2),
            'is_anomaly': bool(row['is_anomaly']),
            'severity': row['severity'] if row['is_anomaly'] else 'normal',
        })

    return {
        'stats': stats,
        'anomalies': anomaly_records,
        'scatter_data': scatter_data,
        'by_region': [{'region': k, 'count': v} for k, v in sorted(by_region.items(), key=lambda x: -x[1])],
        'by_category': [{'category': k, 'count': v} for k, v in sorted(by_category.items(), key=lambda x: -x[1])],
        'score_distribution': {
            'scores': [round(float(s), 4) for s in scores.tolist()],
            'is_anomaly': [bool(a) for a in (predictions == -1).tolist()],
        },
        'model_path': model_path,
        'contamination': contamination,
        'trained_at': datetime.now().isoformat(),
    }


def filter_anomalies(anomalies, filters):
    """Filter anomaly records by date, region, category."""
    result = anomalies
    if filters.get('start_date'):
        result = [a for a in result if a['sale_date'] >= filters['start_date']]
    if filters.get('end_date'):
        result = [a for a in result if a['sale_date'] <= filters['end_date']]
    if filters.get('region'):
        result = [a for a in result if a['region'] == filters['region']]
    if filters.get('category'):
        result = [a for a in result if a['category'] == filters['category']]
    return result
