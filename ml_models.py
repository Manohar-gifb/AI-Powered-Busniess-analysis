"""
ml_models.py - Machine Learning Prediction Module
==================================================
Implements predictive analytics using scikit-learn.

Models:
- Linear Regression (baseline)
- Random Forest Regression (advanced)

Predicts: revenue based on business features.
Saves trained models under models/ directory.
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

warnings.filterwarnings('ignore')

# Try importing ML libraries
try:
    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Models directory
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


def get_sales_dataframe():
    """Load all sales data from SQLite into a Pandas DataFrame."""
    from database import get_db
    conn = get_db()
    df = pd.read_sql_query('''
        SELECT s.sale_date, s.product_id, s.customer_id, s.region, s.category,
               s.quantity, s.unit_price, s.revenue, s.cost, s.profit,
               p.product_name
        FROM sales s
        LEFT JOIN products p ON s.product_id = p.id
    ''', conn)
    conn.close()
    return df


def preprocess_data(df):
    """
    Clean and engineer features for ML models.

    Features created:
    - month, day_of_week, quarter (from sale_date)
    - region_encoded, category_encoded (label encoded)
    - quantity, unit_price (raw numeric)
    - price_x_quantity (interaction feature)
    """
    if df.empty:
        return None, None, {}

    # Parse dates
    df['sale_date'] = pd.to_datetime(df['sale_date'])
    df['month'] = df['sale_date'].dt.month
    df['day_of_week'] = df['sale_date'].dt.dayofweek
    df['quarter'] = df['sale_date'].dt.quarter
    df['year'] = df['sale_date'].dt.year

    # Interaction features
    df['price_x_quantity'] = df['unit_price'] * df['quantity']

    # Encode categorical variables
    le_region = LabelEncoder()
    le_category = LabelEncoder()
    df['region_encoded'] = le_region.fit_transform(df['region'].astype(str))
    df['category_encoded'] = le_category.fit_transform(df['category'].astype(str))

    # Define feature columns
    feature_cols = [
        'quantity', 'unit_price', 'month', 'day_of_week', 'quarter',
        'region_encoded', 'category_encoded', 'price_x_quantity'
    ]

    # Target: revenue
    target_col = 'revenue'

    # Drop any NaN rows
    valid_df = df[feature_cols + [target_col]].dropna()

    if len(valid_df) < 10:
        return None, None, {}

    X = valid_df[feature_cols].values
    y = valid_df[target_col].values

    # Store metadata
    meta = {
        'feature_columns': feature_cols,
        'target_column': target_col,
        'n_samples': len(valid_df),
        'region_classes': le_region.classes_.tolist(),
        'category_classes': le_category.classes_.tolist(),
        'encoders': {'region': le_region, 'category': le_category}
    }

    return X, y, meta


def train_linear_regression(X, y, test_size=0.2, random_state=42):
    """Train a Linear Regression model and return results."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    # Metrics
    metrics = {
        'train_mae': float(mean_absolute_error(y_train, y_pred_train)),
        'test_mae': float(mean_absolute_error(y_test, y_pred_test)),
        'train_rmse': float(np.sqrt(mean_squared_error(y_train, y_pred_train))),
        'test_rmse': float(np.sqrt(mean_squared_error(y_test, y_pred_test))),
        'train_r2': float(r2_score(y_train, y_pred_train)),
        'test_r2': float(r2_score(y_test, y_pred_test)),
        'n_train': len(y_train),
        'n_test': len(y_test),
    }

    # Feature importance (coefficients)
    feature_importance = list(zip(
        ['quantity', 'unit_price', 'month', 'day_of_week', 'quarter',
         'region_encoded', 'category_encoded', 'price_x_quantity'],
        model.coef_.tolist()
    ))
    feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)

    return {
        'model': model,
        'metrics': metrics,
        'feature_importance': feature_importance,
        'X_test': X_test,
        'y_test': y_test,
        'y_pred_test': y_pred_test,
        'y_pred_train': y_pred_train,
        'y_train': y_train,
        'X_train': X_train,
    }


def train_random_forest(X, y, test_size=0.2, random_state=42, n_estimators=100):
    """Train a Random Forest Regression model and return results."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=10,
        min_samples_split=5,
        random_state=random_state,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    # Metrics
    metrics = {
        'train_mae': float(mean_absolute_error(y_train, y_pred_train)),
        'test_mae': float(mean_absolute_error(y_test, y_pred_test)),
        'train_rmse': float(np.sqrt(mean_squared_error(y_train, y_pred_train))),
        'test_rmse': float(np.sqrt(mean_squared_error(y_test, y_pred_test))),
        'train_r2': float(r2_score(y_train, y_pred_train)),
        'test_r2': float(r2_score(y_test, y_pred_test)),
        'n_train': len(y_train),
        'n_test': len(y_test),
    }

    # Feature importance
    feature_names = ['quantity', 'unit_price', 'month', 'day_of_week', 'quarter',
                     'region_encoded', 'category_encoded', 'price_x_quantity']
    feature_importance = list(zip(feature_names, model.feature_importances_.tolist()))
    feature_importance.sort(key=lambda x: x[1], reverse=True)

    return {
        'model': model,
        'metrics': metrics,
        'feature_importance': feature_importance,
        'X_test': X_test,
        'y_test': y_test,
        'y_pred_test': y_pred_test,
        'y_pred_train': y_pred_train,
        'y_train': y_train,
        'X_train': X_train,
    }


def save_model(model, name):
    """Save a trained model to disk."""
    path = os.path.join(MODELS_DIR, f'{name}.joblib')
    joblib.dump(model, path)
    return path


def load_model(name):
    """Load a trained model from disk."""
    path = os.path.join(MODELS_DIR, f'{name}.joblib')
    if os.path.exists(path):
        return joblib.load(path)
    return None


def train_all():
    """
    Full training pipeline:
    1. Load data
    2. Preprocess
    3. Train both models
    4. Save models
    5. Return results
    """
    if not ML_AVAILABLE:
        return {'error': 'scikit-learn or joblib not installed. Run: pip install scikit-learn joblib'}

    # Load and preprocess
    df = get_sales_dataframe()
    if df.empty:
        return {'error': 'No sales data found. Please ensure the database is seeded.'}

    X, y, meta = preprocess_data(df)
    if X is None:
        return {'error': f'Insufficient data for training. Need at least 10 samples, got {len(df)}.'}

    # Train Linear Regression
    lr_result = train_linear_regression(X, y)
    lr_path = save_model(lr_result['model'], 'linear_regression')

    # Train Random Forest
    rf_result = train_random_forest(X, y)
    rf_path = save_model(rf_result['model'], 'random_forest')

    # Save metadata
    meta_save = {k: v for k, v in meta.items() if k != 'encoders'}
    meta_save['trained_at'] = datetime.now().isoformat()
    meta_save['n_samples'] = int(meta_save['n_samples'])
    with open(os.path.join(MODELS_DIR, 'training_meta.json'), 'w') as f:
        json.dump(meta_save, f, indent=2)

    return {
        'linear_regression': {
            'metrics': lr_result['metrics'],
            'feature_importance': lr_result['feature_importance'],
            'model_path': lr_path,
            # Sample predictions for chart (test set, capped at 200 for display)
            'actual': lr_result['y_test'][:200].tolist(),
            'predicted': lr_result['y_pred_test'][:200].tolist(),
        },
        'random_forest': {
            'metrics': rf_result['metrics'],
            'feature_importance': rf_result['feature_importance'],
            'model_path': rf_path,
            'actual': rf_result['y_test'][:200].tolist(),
            'predicted': rf_result['y_pred_test'][:200].tolist(),
        },
        'meta': meta_save,
        'n_samples': int(len(df)),
    }


def predict_revenue(model_name, features):
    """
    Make a prediction with a saved model.

    Args:
        model_name: 'linear_regression' or 'random_forest'
        features: dict with feature values

    Returns:
        predicted revenue value
    """
    model = load_model(model_name)
    if model is None:
        return None

    # Build feature vector
    feature_order = ['quantity', 'unit_price', 'month', 'day_of_week', 'quarter',
                     'region_encoded', 'category_encoded', 'price_x_quantity']

    # Load metadata for encoder classes
    meta_path = os.path.join(MODELS_DIR, 'training_meta.json')
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    else:
        meta = {}

    # Encode region and category
    region_classes = meta.get('region_classes', [])
    category_classes = meta.get('category_classes', [])

    region_enc = region_classes.index(features.get('region', '')) if features.get('region', '') in region_classes else 0
    cat_enc = category_classes.index(features.get('category', '')) if features.get('category', '') in category_classes else 0

    row = [[
        features.get('quantity', 1),
        features.get('unit_price', 50),
        features.get('month', 6),
        features.get('day_of_week', 2),
        features.get('quarter', 2),
        region_enc,
        cat_enc,
        features.get('quantity', 1) * features.get('unit_price', 50),
    ]]

    prediction = model.predict(row)
    return float(prediction[0])
