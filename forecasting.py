"""
forecasting.py - Time-Series Forecasting Module
================================================
Implements business metric forecasting using:
- ARIMA (AutoRegressive Integrated Moving Average)
- Holt-Winters Exponential Smoothing (with trend and seasonality)

Forecasts: revenue, quantity, profit on monthly aggregated data.
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

warnings.filterwarnings('ignore')

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    TS_AVAILABLE = True
except ImportError:
    TS_AVAILABLE = False

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


def get_monthly_data():
    """Load and aggregate sales data by month."""
    from database import get_db
    conn = get_db()
    df = pd.read_sql_query('''
        SELECT sale_date, revenue, quantity, profit
        FROM sales
        ORDER BY sale_date ASC
    ''', conn)
    conn.close()

    if df.empty:
        return None

    df['sale_date'] = pd.to_datetime(df['sale_date'])
    df['month'] = df['sale_date'].dt.to_period('M')

    monthly = df.groupby('month').agg(
        total_revenue=('revenue', 'sum'),
        total_quantity=('quantity', 'sum'),
        total_profit=('profit', 'sum'),
        sale_count=('revenue', 'count'),
    ).reset_index()

    monthly['month_str'] = monthly['month'].astype(str)
    monthly['date'] = pd.to_datetime(monthly['month_str'] + '-01')

    return monthly


def forecast_arima(series, periods=6, order=(1, 1, 1)):
    """
    ARIMA forecasting.

    Args:
        series: pandas Series with datetime index
        periods: number of periods to forecast
        order: ARIMA (p, d, q) parameters

    Returns:
        dict with forecast values, confidence intervals, fitted values
    """
    if not TS_AVAILABLE or len(series) < 4:
        return None

    try:
        model = ARIMA(series.values, order=order)
        fitted = model.fit()

        # Forecast
        result = fitted.get_forecast(steps=periods)
        forecast = result.predicted_mean
        conf_int = result.conf_int(alpha=0.05)

        return {
            'forecast': forecast.tolist(),
            'lower_bound': conf_int[:, 0].tolist(),
            'upper_bound': conf_int[:, 1].tolist(),
            'fitted': fitted.fittedvalues.tolist(),
            'aic': float(fitted.aic),
            'bic': float(fitted.bic),
        }
    except Exception as e:
        return None


def forecast_holtwinters(series, periods=6, seasonal_period=12):
    """
    Holt-Winters Exponential Smoothing with trend and seasonality.

    Args:
        series: pandas Series with datetime index
        periods: number of periods to forecast
        seasonal_period: seasonal周期 (12 for monthly)

    Returns:
        dict with forecast values and fitted values
    """
    if not TS_AVAILABLE or len(series) < seasonal_period * 2:
        # Fall back to simpler model if not enough data
        if len(series) >= 4:
            try:
                model = ExponentialSmoothing(
                    series.values,
                    trend='add',
                    seasonal=None,
                    initialization_method='estimated'
                )
                fitted = model.fit(optimized=True)
                forecast = fitted.forecast(periods)
                return {
                    'forecast': forecast.tolist(),
                    'lower_bound': (forecast * 0.85).tolist(),
                    'upper_bound': (forecast * 1.15).tolist(),
                    'fitted': fitted.fittedvalues.tolist(),
                    'method': 'Holt (no seasonality)',
                }
            except Exception:
                pass
        return None

    try:
        model = ExponentialSmoothing(
            series.values,
            trend='add',
            seasonal='add',
            seasonal_periods=seasonal_period,
            initialization_method='estimated'
        )
        fitted = model.fit(optimized=True)
        forecast = fitted.forecast(periods)

        # Approximate confidence intervals (±15% for Holt-Winters)
        lower = forecast * 0.85
        upper = forecast * 1.15

        return {
            'forecast': forecast.tolist(),
            'lower_bound': lower.tolist(),
            'upper_bound': upper.tolist(),
            'fitted': fitted.fittedvalues.tolist(),
            'method': 'Holt-Winters (trend + seasonality)',
        }
    except Exception as e:
        return None


def generate_forecast(metric='revenue', periods=6, model_type='auto'):
    """
    Main forecasting function.

    Args:
        metric: 'revenue', 'quantity', or 'profit'
        periods: forecast horizon (3, 6, 12 months)
        model_type: 'auto', 'arima', or 'holtwinters'

    Returns:
        dict with all forecast data for the UI
    """
    if not TS_AVAILABLE:
        return {'error': 'statsmodels not installed. Run: pip install statsmodels'}

    monthly = get_monthly_data()
    if monthly is None or len(monthly) < 4:
        return {'error': 'Insufficient historical data. Need at least 4 months.'}

    # Select metric column
    metric_map = {
        'revenue': 'total_revenue',
        'quantity': 'total_quantity',
        'profit': 'total_profit',
    }
    col = metric_map.get(metric, 'total_revenue')

    # Create time series
    series = pd.Series(monthly[col].values, index=monthly['date'])

    # Historical data for display
    historical = []
    for _, row in monthly.iterrows():
        historical.append({
            'date': row['month_str'],
            'value': round(float(row[col]), 2),
        })

    # Generate future dates
    last_date = monthly['date'].max()
    future_dates = pd.date_range(
        start=last_date + pd.offsets.MonthBegin(1),
        periods=periods,
        freq='MS'
    )
    future_labels = [d.strftime('%Y-%m') for d in future_dates]

    # Try models
    result = None

    if model_type in ('auto', 'arima'):
        # Try ARIMA first
        result = forecast_arima(series, periods=periods)
        if result:
            result['model_name'] = 'ARIMA(1,1,1)'

    if result is None and model_type in ('auto', 'holtwinters'):
        # Try Holt-Winters
        result = forecast_holtwinters(series, periods=periods)
        if result:
            result['model_name'] = result.get('method', 'Holt-Winters')

    if result is None and model_type == 'arima':
        # Fall back to Holt-Winters if ARIMA specifically requested but failed
        result = forecast_holtwinters(series, periods=periods)
        if result:
            result['model_name'] = result.get('method', 'Holt-Winters')

    if result is None:
        return {'error': 'Could not fit forecasting model. Try different parameters.'}

    # Format forecast data
    forecast_data = []
    for i, date in enumerate(future_labels):
        forecast_data.append({
            'date': date,
            'value': round(max(0, result['forecast'][i]), 2),
            'lower': round(max(0, result['lower_bound'][i]), 2),
            'upper': round(result['upper_bound'][i], 2),
        })

    # Format fitted values (historical fitted)
    fitted_data = []
    dates = monthly['month_str'].tolist()
    for i, val in enumerate(result['fitted']):
        if i < len(dates):
            fitted_data.append({
                'date': dates[i],
                'value': round(max(0, val), 2),
            })

    # Model metrics
    metrics = {}
    if 'aic' in result:
        metrics['aic'] = round(result['aic'], 2)
    if 'bic' in result:
        metrics['bic'] = round(result['bic'], 2)

    # Calculate MAPE on fitted values
    actuals = monthly[col].values[:len(result['fitted'])]
    fitted_vals = np.array(result['fitted'][:len(actuals)])
    non_zero = actuals != 0
    if non_zero.sum() > 0:
        mape = np.mean(np.abs((actuals[non_zero] - fitted_vals[non_zero]) / actuals[non_zero])) * 100
        metrics['mape'] = round(float(mape), 2)

    return {
        'metric': metric,
        'model_name': result.get('model_name', 'Unknown'),
        'periods': periods,
        'historical': historical,
        'forecast': forecast_data,
        'fitted': fitted_data,
        'metrics': metrics,
        'last_date': monthly['month_str'].max(),
        'total_months': len(monthly),
    }
